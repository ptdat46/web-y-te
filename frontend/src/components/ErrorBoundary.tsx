import React from 'react'

interface State { hasError: boolean }
export default class ErrorBoundary extends React.Component<React.PropsWithChildren, State> {
  state: State = { hasError: false }
  static getDerivedStateFromError(): State { return { hasError: true } }
  render() {
    if (!this.state.hasError) return this.props.children
    return <div className="grid min-h-screen place-items-center bg-[#eaf3ef] p-6"><div className="max-w-md rounded-2xl bg-white p-8 text-center shadow"><h1 className="text-xl font-bold text-teal-950">Đã xảy ra lỗi</h1><p className="mt-2 text-sm text-teal-600">Trang không thể hiển thị. Vui lòng tải lại và thử lại.</p><button onClick={() => window.location.reload()} className="mt-5 rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white">Tải lại trang</button></div></div>
  }
}
