// server.js
const express = require('express');
const sspi = require('node-sspi');
const path = require('path');

const app = express();

// ✅ CommonJS에서는 __dirname이 이미 정의되어 있습니다.
app.use(express.static(path.join(__dirname, 'public')));

// Windows 인증 미들웨어
app.use((req, res, next) => {
  const nodeSSPI = new sspi({ retrieveGroups: true });
  nodeSSPI.authenticate(req, res, (err) => {
    if (!res.finished) next();
  });
});

// 로그인 API
app.get('/api/login', (req, res) => {
  if (req.connection.user) {
    res.json({
      success: true,
      user: req.connection.user,
      groups: req.connection.userGroups || [],
    });
  } else {
    res.status(401).json({ success: false, message: 'Not authenticated' });
  }
});

app.listen(3000, () => {
  console.log('✅ Node server running on http://localhost:3000');
});
