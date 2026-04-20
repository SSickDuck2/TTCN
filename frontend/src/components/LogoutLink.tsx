'use client';

export default function LogoutLink() {
  return (
    <a
      href="/"
      onClick={(e) => {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('token');
        }
      }}
      style={{ color: '#ff4d4f', textDecoration: 'none', marginLeft: '10px' }}
    >
      Đăng xuất
    </a>
  );
}
