// app.js
const express = require('express');
const dotenv = require('dotenv');
const cookieParser = require('cookie-parser');
const helmet = require('helmet');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const authRoutes = require('./routes/auth');

dotenv.config();

const app = express();
const PORT = process.env.PORT || 4000;

app.use(helmet());
app.use(express.json());
app.use(express.urlencoded({ extended: false }));
app.use(cookieParser());

// CORS: 프런트엔드 주소를 허용
app.use(cors({
   origin: true,
  //origin: process.env.FRONTEND_URL || 'http://127.0.0.1:5501',
  credentials: true
}));

// 기본 요청률 제한
const limiter = rateLimit({
  windowMs: 1 * 60 * 1000, // 1분
  max: 100
});
app.use(limiter);

app.use('/api/auth', authRoutes);

app.get('/', (req, res) => {
  res.send({ message: 'Hull3D auth backend running' });
});

// 에러 핸들러
app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: '서버 오류' });
});

app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
