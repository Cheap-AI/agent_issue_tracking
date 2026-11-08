/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return {
      // "/" 첫 진입 시 영화 랜딩 페이지(public/landing.html)를 보여준다.
      beforeFiles: [{ source: '/', destination: '/landing.html' }],
      afterFiles: [
        {
          source: '/api/:path*',
          destination: 'http://127.0.0.1:8000/api/:path*',
        },
      ],
      fallback: [],
    };
  },
};

module.exports = nextConfig;
