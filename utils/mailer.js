// utils/mailer.js
const nodemailer = require('nodemailer');
const dotenv = require('dotenv');
dotenv.config();

const transporter = nodemailer.createTransport({
  host: process.env.EMAIL_HOST,
  port: Number(process.env.EMAIL_PORT || 587),
  secure: Number(process.env.EMAIL_PORT) === 465, // true for 465, false for other ports
  auth: {
    user: process.env.EMAIL_USER,
    pass: process.env.EMAIL_PASS
  }
});

async function sendResetEmail(to, resetLink) {
  const info = await transporter.sendMail({
    from: `"Hull3D Support" <${process.env.EMAIL_USER}>`,
    to,
    subject: "비밀번호 재설정 링크",
    text: `비밀번호 재설정 링크: ${resetLink}`,
    html: `<p>비밀번호 재설정 링크:</p><p><a href="${resetLink}">${resetLink}</a></p>`
  });
  return info;
}

module.exports = { sendResetEmail };
