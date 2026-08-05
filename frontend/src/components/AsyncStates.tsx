import { AlertCircle, Loader2, RefreshCw } from 'lucide-react';

export function Loading({ message = '불러오는 중...', padding = 64 }: { message?: string; padding?: number }) {
  return (
    <div style={{ textAlign: 'center', padding }}>
      <Loader2 size={36} className="spinning" style={{ color: 'var(--primary)', marginBottom: 12 }} />
      <p style={{ color: 'var(--text-secondary)' }}>{message}</p>
    </div>
  );
}

/**
 * 에러를 조용히 삼키지 않고 원인과 다음 행동을 같이 보여준다.
 * 백엔드가 안 떠 있는 상태가 가장 흔한 실패라, 그 경우 실행 방법을 직접 안내한다.
 */
export function ErrorBox({ error, onRetry }: { error: string; onRetry?: () => void }) {
  const isOffline = error.includes('연결할 수 없습니다');
  return (
    <div className="glass-card" style={{ padding: 32, textAlign: 'center' }}>
      <AlertCircle size={36} style={{ color: 'var(--error, #ef4444)', marginBottom: 12 }} />
      <p style={{ color: 'var(--text-secondary)', marginBottom: isOffline ? 12 : 20 }}>{error}</p>
      {isOffline && (
        <pre style={{
          textAlign: 'left', display: 'inline-block', margin: '0 auto 20px',
          padding: '12px 16px', borderRadius: 'var(--radius-md)',
          background: 'rgba(0,0,0,0.25)', fontFamily: 'var(--font-mono)',
          fontSize: '0.78rem', color: 'var(--text-tertiary)', lineHeight: 1.7,
        }}>
{`docker compose up -d
cd backend && ./mvnw spring-boot:run`}
        </pre>
      )}
      {onRetry && (
        <div>
          <button className="btn btn-ghost" onClick={onRetry}>
            <RefreshCw size={14} /> 다시 시도
          </button>
        </div>
      )}
    </div>
  );
}

export function EmptyState({ icon, title, hint }: { icon: React.ReactNode; title: string; hint?: string }) {
  return (
    <div className="glass-card" style={{ padding: 48, textAlign: 'center' }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 12 }}>{icon}</div>
      <p style={{ color: 'var(--text-tertiary)', marginBottom: hint ? 8 : 0 }}>{title}</p>
      {hint && <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{hint}</p>}
    </div>
  );
}
