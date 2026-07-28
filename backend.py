"""
Backend nhỏ (FastAPI) đứng giữa web và vnstock.

Vì vnstock là thư viện Python, trình duyệt (JavaScript) không gọi thẳng
được — cần 1 server nhỏ nhận request từ web, gọi vnstock, trả JSON về.
Đây cũng chính là phần "backend tự động hoá" giúp khắc phục lỗ hổng
"không có server, mọi thứ chạy client-side" đã nêu trong báo cáo trước.

CÁCH CHẠY THỬ LOCAL:
1. pip install fastapi uvicorn vnstock
2. python backend.py
3. Mở trình duyệt: http://localhost:8000/api/stock/VCB
   -> nếu thấy JSON dữ liệu là chạy đúng.

CÁCH DEPLOY (để web thật dùng được, không chỉ chạy trên máy bạn):
- Đẩy code này lên GitHub (1 repo riêng, ví dụ ten-du-an-backend)
- Deploy trên Render.com (free tier, hỗ trợ Python tốt hơn Vercel cho việc này):
  1. Vào render.com -> New -> Web Service -> chọn repo GitHub
  2. Build Command: pip install -r requirements.txt
  3. Start Command: uvicorn backend:app --host 0.0.0.0 --port 10000
  4. Deploy xong sẽ có link dạng https://ten-du-an-backend.onrender.com
- Copy link đó, dán vào biến BACKEND_URL trong file HTML (đã hướng dẫn bên dưới)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from vnstock import Vnstock

app = FastAPI(title="BayDanChungKhoan Backend")

# Cho phép web (chạy trên domain khác, ví dụ Vercel) gọi được API này.
# Khi deploy thật, nên thay "*" bằng đúng domain frontend để an toàn hơn.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "message": "Backend đang chạy. Thử /api/stock/VCB"}


@app.get("/api/stock/{ticker}")
def get_stock_data(ticker: str, start: str = "2023-01-01", end: str = "2026-07-27"):
    """
    Trả về dữ liệu Date/Close/Volume của 1 mã, đúng định dạng
    dashboard cần — web sẽ gọi endpoint này thay vì bắt user upload CSV.
    """
    ticker = ticker.strip().upper()

    try:
        stock = Vnstock().stock(symbol=ticker, source="VCI")
        df = stock.quote.history(start=start, end=end, interval="1D")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Không lấy được dữ liệu từ vnstock: {e}")

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy dữ liệu cho mã {ticker}")

    df = df.rename(columns={"time": "Date", "close": "Close", "volume": "Volume"})
    df["Date"] = df["Date"].astype(str).str[:10]  # chuẩn hoá yyyy-mm-dd
    df = df[["Date", "Close", "Volume"]].dropna().sort_values("Date")

    if len(df) < 80:
        raise HTTPException(
            status_code=422,
            detail=f"Mã {ticker} chỉ có {len(df)} phiên, dưới ngưỡng tối thiểu 80 phiên."
        )

    return {
        "ticker": ticker,
        "count": len(df),
        "data": df.to_dict(orient="records")
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
