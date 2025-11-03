// routes/auth.js
const express = require('express');
const router = express.Router();
const pool = require('../db');
const bcrypt = require('bcrypt');
const validator = require('validator');
const jwt = require('jsonwebtoken');
const dotenv = require('dotenv');
const { v4: uuidv4 } = require('uuid');
const { sendResetEmail } = require('../utils/mailer');

dotenv.config();
const JWT_SECRET = process.env.JWT_SECRET || 'changeme';
const COOKIE_NAME = process.env.COOKIE_NAME || 'token';
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://192.168.10.12:3000';

// helper: create JWT
function createToken(payload) {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: process.env.JWT_EXPIRES_IN || '1d' });
}

// 회원가입
router.post('/register', async (req, res) => {
  try {
    const { name, email, department, password, confirmPassword } = req.body;

    if (!name || !email || !password || !confirmPassword) {
      return res.status(400).json({ error: '필수 항목이 누락되었습니다.' });
    }
    if (!validator.isEmail(email)) return res.status(400).json({ error: '유효한 이메일을 입력하세요.' });
    if (password.length < 8) return res.status(400).json({ error: '비밀번호는 8자 이상이어야 합니다.' });
    if (password !== confirmPassword) return res.status(400).json({ error: '비밀번호가 일치하지 않습니다.' });

    const conn = await pool.getConnection();
    try {
      const [rows] = await conn.query('SELECT id FROM users WHERE email = ?', [email]);
      if (rows.length > 0) {
        return res.status(409).json({ error: '이미 등록된 이메일입니다.' });
      }
      const hash = await bcrypt.hash(password, 12);
      await conn.query(
        'INSERT INTO users (name, email, department, password_hash) VALUES (?, ?, ?, ?)',
        [name, email, department || null, hash]
      );
      return res.json({ message: '회원가입이 완료되었습니다.' });
    } finally {
      conn.release();
    }
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: '서버 오류' });
  }
});

// 로그인
router.post('/login', async (req, res) => {
  try {
    const { email, password, remember } = req.body;
    if (!email || !password) return res.status(400).json({ error: '이메일과 비밀번호를 입력하세요.' });

    const conn = await pool.getConnection();
    try {
      const [rows] = await conn.query('SELECT id, name, email, department, password_hash FROM users WHERE email = ?', [email]);
      if (rows.length === 0) return res.status(401).json({ error: '등록되지 않은 이메일입니다.' });

      const user = rows[0];
      const match = await bcrypt.compare(password, user.password_hash);
      if (!match) return res.status(401).json({ error: '비밀번호가 일치하지 않습니다.' });

      const token = createToken({ id: user.id, email: user.email });
      // 쿠키 설정: remember flag에 따라 만료기간 다르게 설정
      const cookieOptions = {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax'
      };
      if (remember) {
        // 30일
        cookieOptions.maxAge = 30 * 24 * 60 * 60 * 1000;
      } else {
        // 기본 1일 (JWT 만료와 일치)
        cookieOptions.maxAge = 24 * 60 * 60 * 1000;
      }
      res.cookie(COOKIE_NAME, token, cookieOptions);
      return res.json({ message: '로그인 성공', user: { id: user.id, name: user.name, email: user.email, department: user.department } });
    } finally {
      conn.release();
    }
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: '서버 오류' });
  }
});

// 로그아웃
router.post('/logout', (req, res) => {
  res.clearCookie(COOKIE_NAME);
  return res.json({ message: '로그아웃되었습니다.' });
});

// 비밀번호 재설정 요청(메일 발송)
router.post('/forgot-password', async (req, res) => {
  try {
    const { email } = req.body;
    if (!email || !validator.isEmail(email)) return res.status(400).json({ error: '유효한 이메일을 입력하세요.' });

    const token = uuidv4();
    const expires = new Date(Date.now() + 60 * 60 * 1000); // 1시간

    const conn = await pool.getConnection();
    try {
      const [rows] = await conn.query('SELECT id FROM users WHERE email = ?', [email]);
      if (rows.length === 0) {
        // 보안상 이메일이 없어도 같은 응답을 보냄
        return res.json({ message: '비밀번호 재설정 링크가 이메일로 전송되었습니다.' });
      }
      await conn.query('UPDATE users SET reset_token = ?, reset_expires = ? WHERE email = ?', [token, expires, email]);
    } finally {
      conn.release();
    }

    const resetLink = `${FRONTEND_URL}/reset-password?token=${token}&email=${encodeURIComponent(email)}`;
    // 실제 운영: 이메일 전송
    try {
      await sendResetEmail(email, resetLink);
    } catch (mailErr) {
      console.error('메일 전송 실패:', mailErr);
      // 이메일 실패해도 사용자에게 일반 응답
    }

    return res.json({ message: '비밀번호 재설정 링크가 이메일로 전송되었습니다.' });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: '서버 오류' });
  }
});

// 비밀번호 재설정 (토큰 검사 후 비밀번호 변경)
router.post('/reset-password', async (req, res) => {
  try {
    const { email, token, newPassword } = req.body;
    if (!email || !token || !newPassword) return res.status(400).json({ error: '필수 항목 누락' });
    if (newPassword.length < 8) return res.status(400).json({ error: '비밀번호는 8자 이상이어야 합니다.' });

    const conn = await pool.getConnection();
    try {
      const [rows] = await conn.query('SELECT id, reset_expires FROM users WHERE email = ? AND reset_token = ?', [email, token]);
      if (rows.length === 0) return res.status(400).json({ error: '유효하지 않은 토큰입니다.' });

      const user = rows[0];
      const now = new Date();
      if (!user.reset_expires || new Date(user.reset_expires) < now) {
        return res.status(400).json({ error: '토큰이 만료되었습니다.' });
      }
      const hash = await bcrypt.hash(newPassword, 12);
      await conn.query('UPDATE users SET password_hash = ?, reset_token = NULL, reset_expires = NULL WHERE id = ?', [hash, user.id]);
      return res.json({ message: '비밀번호가 변경되었습니다. 로그인하세요.' });
    } finally {
      conn.release();
    }
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: '서버 오류' });
  }
});

// 안전한 프로필 조회 (인증 필요)
router.get('/me', async (req, res) => {
  try {
    const token = req.cookies[COOKIE_NAME] || req.header('Authorization')?.replace('Bearer ', '');
    if (!token) return res.status(401).json({ error: '인증 필요' });

    let payload;
    try {
      payload = jwt.verify(token, JWT_SECRET);
    } catch (e) {
      return res.status(401).json({ error: '토큰이 유효하지 않습니다.' });
    }

    const conn = await pool.getConnection();
    try {
      const [rows] = await conn.query('SELECT id, name, email, department, created_at FROM users WHERE id = ?', [payload.id]);
      if (rows.length === 0) return res.status(404).json({ error: '사용자를 찾을 수 없습니다.' });
      const u = rows[0];
      return res.json({ user: u });
    } finally {
      conn.release();
    }
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: '서버 오류' });
  }
});

// 트리 구조로 변환하는 함수
function buildTree(data, parentId = null) {
  return data
    .filter(item => item.parent_id === parentId)
    .map(item => ({
      id: item.id,
      text: item.text,
      children: buildTree(data, item.id)
    }));
}


router.post('/getBlockTree', async (req, res) => {
  try {
    const { block } = req.body;
    const conn = await pool.getConnection();
    const rows = await conn.query('SELECT id, parent_id, text FROM tree_nodes WHERE block = ?', [block]);
    conn.release();

    const tree = buildTree(rows[0]);
    res.json(tree);
  } catch (err) {
    console.error(err);
    res.status(500).send('DB 오류');
  }
});

module.exports = router;
