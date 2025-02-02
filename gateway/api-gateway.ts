import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';

const app = express();

// Rate limiting middleware
app.use(rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100
}));

// Route definitions
app.use('/signals', createProxyMiddleware({ 
  target: 'http://signal-processor:3000',
  changeOrigin: true 
}));

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'healthy' });
}); 