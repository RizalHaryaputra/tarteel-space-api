import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from core.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FRONTEND_URL


def send_reset_email(to_email: str, token: str) -> None:
    """Kirim email berisi link reset password ke pengguna."""
    reset_link = f"{FRONTEND_URL}/reset-password?token={token}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset Password — Tarteel Space"
    msg["From"]    = f"Tarteel Space <{SMTP_USER}>"
    msg["To"]      = to_email

    # Versi plain text
    text_body = f"""Halo,

Kami menerima permintaan untuk mereset password akun Tarteel Space Anda.

Klik link berikut untuk mengatur password baru (berlaku 15 menit):
{reset_link}

Jika Anda tidak meminta reset password, abaikan email ini.

Salam,
Tim Tarteel Space
"""

    # Versi HTML
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
</head>
<body style="margin:0;padding:0;background-color:#0f172a;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="background-color:#1e293b;border-radius:16px;border:1px solid #334155;overflow:hidden;">

          <!-- Header -->
          <tr>
            <td align="center" style="padding:32px 40px 24px;background:linear-gradient(135deg,#1e40af22,#0f172a);">
              <div style="font-size:28px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;">
                Tarteel <span style="color:#60a5fa;">Space</span>
              </div>
              <div style="margin-top:6px;font-size:13px;color:#94a3b8;">Platform Evaluasi Pelafalan Hijaiyah</div>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px 40px;">
              <h2 style="margin:0 0 12px;font-size:20px;color:#f1f5f9;font-weight:700;">Reset Password Anda</h2>
              <p style="margin:0 0 24px;font-size:14px;color:#94a3b8;line-height:1.7;">
                Kami menerima permintaan untuk mereset password akun Tarteel Space yang terdaftar dengan alamat email ini.
                Klik tombol di bawah untuk mengatur password baru.
              </p>

              <!-- CTA Button -->
              <table cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td align="center" style="padding:8px 0 28px;">
                    <a href="{reset_link}"
                       style="display:inline-block;background:linear-gradient(135deg,#2563eb,#3b82f6);color:#ffffff;
                              text-decoration:none;font-weight:700;font-size:15px;padding:14px 36px;
                              border-radius:10px;letter-spacing:0.3px;">
                      Reset Password →
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Warning -->
              <div style="background:#0f172a;border:1px solid #334155;border-radius:10px;padding:16px 20px;margin-bottom:24px;">
                <p style="margin:0;font-size:12px;color:#64748b;line-height:1.6;">
                  ⏱️ <strong style="color:#94a3b8;">Link berlaku selama 15 menit.</strong><br/>
                  Jika Anda tidak meminta reset password, abaikan email ini — akun Anda tetap aman.
                </p>
              </div>

              <!-- Fallback URL -->
              <p style="margin:0;font-size:11px;color:#475569;line-height:1.6;">
                Jika tombol di atas tidak berfungsi, salin dan tempel URL berikut ke browser:<br/>
                <a href="{reset_link}" style="color:#60a5fa;word-break:break-all;">{reset_link}</a>
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:20px 40px;border-top:1px solid #1e293b;text-align:center;">
              <p style="margin:0;font-size:11px;color:#475569;">
                © 2026 Tarteel Space · Dikembangkan oleh Rizal Haryaputra · Teknologi Informasi UNY
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())

    print(f"[Email] Reset password email sent to: {to_email}")
