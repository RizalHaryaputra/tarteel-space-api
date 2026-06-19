import io
import numpy as np
import librosa
from core.config import (
    SAMPLE_RATE, MAX_LEN, N_MFCC, N_FFT, HOP_LEN, TEMPERATURE
)

try:
    from ai_edge_litert.interpreter import Interpreter # type: ignore
except ImportError:
    try:
        from tflite_runtime.interpreter import Interpreter # type: ignore
    except ImportError:
        import tensorflow.lite as tflite
        Interpreter = tflite.Interpreter

# Global dictionary to hold model, label map, and normalization stats
ml_state = {}

def load_audio_robust(audio_bytes: bytes) -> tuple:
    """
    Load audio bytes → numpy array float32 [-1, 1] pada SAMPLE_RATE.
    """
    import av
    import soundfile as sf

    buf = io.BytesIO(audio_bytes)

    # 1. PyAV fallback
    try:
        buf.seek(0)
        container = av.open(buf)
        stream = container.streams.audio[0]
        orig_sr = stream.sample_rate

        frames_data = []
        for frame in container.decode(stream):
            arr = frame.to_ndarray()

            if arr.dtype == np.int16:
                arr = arr.astype(np.float32) / 32768.0
            elif arr.dtype == np.float32:
                pass
            else:
                arr = arr.astype(np.float32)
                mx = np.abs(arr).max()
                if mx > 0:
                    arr = arr / mx

            frames_data.append(arr)

        if not frames_data:
            raise ValueError("Tidak ada frame audio")

        y = np.concatenate(frames_data, axis=1)
        y = y.mean(axis=0) if y.shape[0] > 1 else y[0]
        y = np.clip(y, -1.0, 1.0)

        if orig_sr != SAMPLE_RATE:
            y = librosa.resample(y, orig_sr=orig_sr, target_sr=SAMPLE_RATE)

        print(f"[Audio] PyAV OK | sr={orig_sr} | samples={len(y)} | peak={np.abs(y).max():.3f}")
        return y, SAMPLE_RATE

    except Exception as e:
        print(f"[Audio] PyAV gagal: {e}")

    # 2. soundfile fallback
    try:
        buf.seek(0)
        y, orig_sr = sf.read(buf, dtype='float32', always_2d=False)
        if y.ndim == 2:
            y = y.mean(axis=1)
        if orig_sr != SAMPLE_RATE:
            y = librosa.resample(y, orig_sr=orig_sr, target_sr=SAMPLE_RATE)
        print(f"[Audio] soundfile OK | sr={orig_sr} | samples={len(y)}")
        return y, SAMPLE_RATE
    except Exception as e:
        print(f"[Audio] soundfile gagal: {e}")

    # 3. librosa fallback
    try:
        buf.seek(0)
        y, sr = librosa.load(buf, sr=SAMPLE_RATE, mono=True)
        print(f"[Audio] librosa OK | sr={sr} | samples={len(y)}")
        return y, sr
    except Exception as e:
        raise ValueError(f"Format audio tidak dikenali. Detail: {e}")


def preprocess_and_extract_mfcc(audio_bytes: bytes) -> np.ndarray:
    """
    Proses audio bytes → MFCC 3-channel siap inferensi.
    """
    y, sr = load_audio_robust(audio_bytes)

    if len(y) == 0:
        raise ValueError("Audio kosong. Coba rekam ulang.")

    peak = np.max(np.abs(y))
    if peak < 0.015:
        raise ValueError("Suara tidak terdeteksi atau terlalu pelan. Bicara lebih dekat ke mikrofon.")

    y = y / peak
    y, _ = librosa.effects.trim(y, top_db=20)

    if len(y) == 0:
        raise ValueError("Audio hanya berisi keheningan setelah diproses.")

    if len(y) < MAX_LEN:
        y = np.pad(y, (0, MAX_LEN - len(y)), mode="constant")
    else:
        y = y[:MAX_LEN]

    mfcc = librosa.feature.mfcc(y=y, sr=SAMPLE_RATE, n_mfcc=N_MFCC, n_fft=N_FFT, hop_length=HOP_LEN)
    delta_mfcc = librosa.feature.delta(mfcc)
    delta2_mfcc = librosa.feature.delta(mfcc, order=2)

    combined = np.stack([mfcc, delta_mfcc, delta2_mfcc], axis=0)
    combined = np.transpose(combined, (1, 2, 0))

    mean = ml_state.get("norm_mean", 0.0)
    std = ml_state.get("norm_std", 1.0)
    combined = (combined - mean) / (std + 1e-8)

    return combined.astype(np.float32)


def softmax_with_temperature(logits: np.ndarray, temperature: float) -> np.ndarray:
    logits = logits / temperature
    logits = logits - np.max(logits)
    exp = np.exp(logits)
    return exp / np.sum(exp)


def run_inference(mfcc_feature: np.ndarray, expected_label: str = None) -> tuple[str, float, list, float, list]:
    interpreter = ml_state["interpreter"]
    input_details = ml_state["input_details"]
    output_details = ml_state["output_details"]
    idx2label = ml_state["idx2label"]
    label2idx = ml_state.get("label2idx", {})

    input_data = np.expand_dims(mfcc_feature, axis=0)
    
    # Run TFLite inference
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    raw_output = interpreter.get_tensor(output_details[0]['index'])[0]

    if abs(raw_output.sum() - 1.0) < 0.01:
        logit_proxy = np.log(np.clip(raw_output, 1e-9, 1.0))
        output = softmax_with_temperature(logit_proxy, TEMPERATURE)
    else:
        output = softmax_with_temperature(raw_output, TEMPERATURE)

    top_idx = int(np.argmax(output))
    top_label = idx2label[top_idx]
    confidence = float(output[top_idx]) * 100.0

    expected_confidence = 0.0
    if expected_label:
        exp_idx = None
        for key, idx in label2idx.items():
            if expected_label in key:
                exp_idx = idx
                break
        if exp_idx is not None:
            expected_confidence = float(output[exp_idx]) * 100.0
    elif expected_label is None:
        expected_confidence = confidence

    top3_idx = np.argsort(output)[::-1][:3]
    top3 = [{"label": idx2label[i], "score": round(float(output[i])*100, 2)} for i in top3_idx]

    top5_idx = np.argsort(output)[::-1][:5]
    top5 = [{"label": idx2label[i], "score": round(float(output[i])*100, 2)} for i in top5_idx]
    print(f"[Inference] Top-5: " + " | ".join(f"{idx2label[i]}={output[i]*100:.1f}%" for i in top5_idx))
    if expected_label:
        print(f"[Inference] Target: {expected_label} = {expected_confidence:.1f}%")

    return top_label, confidence, top3, expected_confidence, top5


def reload_and_warmup_model(model_path: str, mean_path: str, std_path: str, label_path: str):
    """
    Muat file model/mean/std ke memori sementara, lakukan warm-up inferensi,
    lalu lakukan atomic swap ke `ml_state` global agar user tidak mengalami downtime.
    """
    import json
    import io
    import soundfile as sf
    import time

    start_time = time.time()
    print("[Model] Memulai proses Reload & Warm-up (Background)...")

    # 1. Load ke variabel sementara
    new_interpreter = Interpreter(model_path=str(model_path))
    new_interpreter.allocate_tensors()
    new_input_details = new_interpreter.get_input_details()
    new_output_details = new_interpreter.get_output_details()

    with open(label_path) as f:
        mapping = json.load(f)
    new_idx2label = {int(k): v for k, v in mapping["idx2label"].items()}
    new_label2idx = mapping["label2idx"]

    new_norm_mean = float(np.load(mean_path)[0])
    new_norm_std = float(np.load(std_path)[0])

    # 2. Warm-up
    print("[Model] Melakukan warm-up pada model baru...")
    sr = 22050
    t = np.linspace(0, 1, sr, endpoint=False)
    dummy_audio = 0.5 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
    
    buf = io.BytesIO()
    sf.write(buf, dummy_audio, sr, format='WAV')
    wav_bytes = buf.getvalue()
    
    # Gunakan norm sementara untuk preprocessing warm-up
    old_mean = ml_state.get("norm_mean")
    old_std = ml_state.get("norm_std")
    ml_state["norm_mean"] = new_norm_mean
    ml_state["norm_std"] = new_norm_std
    
    try:
        dummy_mfcc = preprocess_and_extract_mfcc(wav_bytes)
        
        # Fake inference pada model baru
        input_data = np.expand_dims(dummy_mfcc, axis=0)
        new_interpreter.set_tensor(new_input_details[0]['index'], input_data)
        new_interpreter.invoke()
        _ = new_interpreter.get_tensor(new_output_details[0]['index'])[0]
    except Exception as e:
        # Revert norm sementara jika gagal
        if old_mean is not None: ml_state["norm_mean"] = old_mean
        if old_std is not None: ml_state["norm_std"] = old_std
        print(f"[Model] Warm-up gagal: {e}")
        raise e

    # 3. ATOMIC SWAP
    ml_state["interpreter"] = new_interpreter
    ml_state["input_details"] = new_input_details
    ml_state["output_details"] = new_output_details
    ml_state["idx2label"] = new_idx2label
    ml_state["label2idx"] = new_label2idx
    ml_state["norm_mean"] = new_norm_mean
    ml_state["norm_std"] = new_norm_std

    elapsed = time.time() - start_time
    print(f"[Model] Reload & Atomic Swap berhasil dalam {elapsed:.2f} detik! Model siap melayani.")
