import { Icon, type IconName } from '../components/Icon'
import { LargeTitle } from '../components/Page'
import { stagger } from '../lib/motion'

const COMING: { icon: IconName; title: string; sub: string }[] = [
  { icon: 'wallet', title: '결제한 사람별 돌려줄 돈', sub: '승인된 지출을 사람별로 모아서 보여줘요' },
  { icon: 'checkCircle', title: '보냈어요 표시', sub: '송금은 각자 하고, 여기선 보낸 것만 표시해요' },
  { icon: 'receipt', title: '계정별 예산 잔액', sub: '얼마 썼고 얼마 남았는지, 넘을 것 같으면 알려줘요' },
]

/** 정산 (5단계에서 만듦: 승인 → 결제자별 환급 집계 → 환급 완료 처리 → 예산 잔액) */
export function SettlementPage() {
  return (
    <>
      <div className="topbar-spacer" aria-hidden="true" />
      <div className="screen screen--with-tabbar">
        <LargeTitle title="정산" subtitle="승인된 지출을 결제한 사람에게 돌려줘요" />
        <section className="card anim-rise" style={stagger(1)}>
          <div className="empty" style={{ paddingBottom: 12 }}>
            <span className="empty__icon" style={{ background: 'var(--primary-weak)', color: 'var(--primary)' }}>
              <Icon name="wallet" />
            </span>
            <p className="empty__title">승인 기능이 생기면 여기서 정산해요</p>
            <p className="empty__desc">지금은 영수증 등록과 제출까지 할 수 있어요</p>
          </div>
        </section>
        <section className="card card--list anim-rise" style={stagger(2)} aria-label="곧 생기는 기능">
          <div className="card__head">
            <h2 className="card__title">곧 생겨요</h2>
          </div>
          <ul className="rows" style={{ marginTop: 6 }}>
            {COMING.map((item) => (
              <li key={item.title} className="row-item">
                <span className="tile" style={{ background: 'var(--surface-2)', color: 'var(--text-2)' }}>
                  <Icon name={item.icon} size={22} />
                </span>
                <span className="row-item__main">
                  <span className="row-item__title">{item.title}</span>
                  <span className="row-item__sub" style={{ whiteSpace: 'normal' }}>
                    {item.sub}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </>
  )
}
