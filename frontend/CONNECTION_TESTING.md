# Frontend-Backend Connection Testing Guide

## 🎯 Quick Verification Steps

### 1. Check Backend is Running
Open a browser and visit: `http://localhost:8000/health`

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "HiddenGem Trading API",
  "version": "0.1.0",
  "environment": "development"
}
```

If you don't see this, the backend is not running or not accessible.

### 2. Check Frontend is Running
Open a browser and visit: `http://localhost:5188`

You should see:
- **Header**: Two status indicators
  - 🟢 "后端正常" (Backend Normal) - Green badge
  - 🔴 "后端断开" (Backend Disconnected) - Red badge if not connected
  - ⚪ "实时连接" or "已断开" (WebSocket status)

### 3. Check Browser Console
Open browser DevTools (F12), go to the **Console** tab and look for:

✅ **Good Signs:**
- No red errors
- Successful API calls logged
- `GET http://localhost:8000/health` returns 200
- `GET http://localhost:8000/api/v1/portfolio/summary` returns 200

❌ **Problem Signs:**
- CORS errors
- Network errors
- 404 Not Found errors
- Connection refused errors

## 🔧 Common Issues and Solutions

### Issue 1: CORS Error

**Symptoms:**
```
Access to XMLHttpRequest at 'http://localhost:8000/api/v1/portfolio/summary'
from origin 'http://localhost:5188' has been blocked by CORS policy
```

**Solution:**
Add CORS middleware to your FastAPI backend:

```python
# In backend/api/main.py
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5188"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Issue 2: Backend Not Running

**Symptoms:**
- Header shows "后端断开" (red badge)
- Dashboard shows error message
- Console shows: `ERR_CONNECTION_REFUSED`

**Solution:**
Start the backend server:
```bash
cd backend
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Issue 3: Wrong Backend URL

**Symptoms:**
- API calls go to wrong address
- 404 errors for all endpoints

**Solution:**
Check your `.env` file in the frontend directory:
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

After changing `.env`, restart the frontend dev server:
```bash
npm run dev
```

### Issue 4: No Data Displayed

**Symptoms:**
- Backend connected (green badge)
- But dashboard shows "暂无数据" (No data)
- No errors in console

**Solution:**
The backend might not have any data yet. Check backend responses:

```bash
# Check portfolio
curl http://localhost:8000/api/v1/portfolio/summary

# Check signals
curl http://localhost:8000/api/v1/signals/current

# Check agents
curl http://localhost:8000/api/v1/agents/status
```

If these return empty arrays or null values, the backend needs to be initialized with data.

### Issue 5: WebSocket Not Connected

**Symptoms:**
- Backend API connected (green)
- But "实时连接" shows "已断开" (gray badge)

**Solution:**
WebSocket connections are separate from HTTP. The frontend creates WebSocket clients but doesn't auto-connect them by default.

To enable WebSocket connections, the backend needs to implement WebSocket endpoints at:
- `ws://localhost:8000/ws/market`
- `ws://localhost:8000/ws/orders`
- `ws://localhost:8000/ws/portfolio`
- `ws://localhost:8000/ws/agents`

## 🧪 Testing the Connection

### Test 1: API Health Check
```bash
curl http://localhost:8000/health
```

Expected: 200 OK with health status

### Test 2: Portfolio API
```bash
curl http://localhost:8000/api/v1/portfolio/summary
```

Expected: 200 OK with portfolio data (might be empty initially)

### Test 3: Agents Status
```bash
curl http://localhost:8000/api/v1/agents/status
```

Expected: 200 OK with array of agents

### Test 4: Open DevTools Network Tab

1. Open browser DevTools (F12)
2. Go to **Network** tab
3. Reload the page (Ctrl+R)
4. Look for these requests:

**Should succeed (200 OK):**
- `GET /health`
- `GET /api/v1/portfolio/summary`
- `GET /api/v1/signals/current`
- `GET /api/v1/agents/status`

**Check the response:**
Click on each request → **Preview** tab to see the data

### Test 5: Check Dashboard Data Loading

The Dashboard page now:
1. Shows a loading spinner initially
2. Fetches data from 3 endpoints:
   - Portfolio summary
   - Trading signals
   - Agents status
3. Displays data or error messages
4. Auto-refreshes every few seconds

**What you should see:**

✅ **With Backend Running:**
- Loading spinner briefly appears
- Data appears in cards
- Numbers update (even if 0)
- Agent status shows enabled/disabled

❌ **Without Backend:**
- Error card appears with diagnostic info
- "无法连接到后端服务" message
- Checklist for troubleshooting

## 📊 Verifying Data Display

### Portfolio Section
Should show:
- Total value: ¥X.XX
- Daily P&L: colored red/green
- Number of positions
- Cash amount

### Signals Section
- List of recent signals (if any)
- Signal direction (买入/卖出/持有)
- Agent name
- Entry price
- Timestamp

### Agents Section
- 7 agent cards (technical, fundamental, risk, market, policy, sentiment, execution)
- Green dot = enabled, gray dot = disabled
- "运行中" or "已停用" status

## 🔍 Debugging Tips

### 1. Check Console Logs
Open DevTools → Console tab:
```javascript
// You should see these queries running:
['portfolio', 'summary']
['signals', 'current']
['agents', 'status']
['health']
```

### 2. Check Network Tab
Open DevTools → Network tab:
- Filter by "Fetch/XHR"
- Look for API calls to `localhost:8000`
- Click on any failed request to see error details

### 3. Test API Directly
Use curl or Postman to test backend endpoints independently:
```bash
# Test all main endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/portfolio/summary
curl http://localhost:8000/api/v1/signals/current
curl http://localhost:8000/api/v1/agents/status
curl http://localhost:8000/api/v1/orders/
```

### 4. Check Backend Logs
Watch backend console for incoming requests:
```
INFO:     127.0.0.1:XXXXX - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:XXXXX - "GET /api/v1/portfolio/summary HTTP/1.1" 200 OK
```

### 5. Verify Environment Variables
In the browser console, run:
```javascript
console.log('API URL:', import.meta.env.VITE_API_BASE_URL);
console.log('WS URL:', import.meta.env.VITE_WS_URL);
```

Should output:
```
API URL: http://localhost:8000
WS URL: ws://localhost:8000
```

## ✅ Success Indicators

You'll know the connection is working when:

1. **Header shows:**
   - 🟢 "后端正常" (Backend Normal) - green badge
   - Backend version in tooltip

2. **Dashboard displays:**
   - Actual numbers (not just ¥0.00)
   - Portfolio data from backend
   - Agent status indicators
   - No error messages

3. **Console shows:**
   - No red errors
   - Successful API calls (200 status)
   - React Query cache updates

4. **Network tab shows:**
   - Successful requests to backend
   - Proper JSON responses
   - Auto-refresh requests every few seconds

## 🚀 Next Steps After Connection Works

1. **Add Sample Data to Backend**
   - Create test strategies
   - Add sample portfolio positions
   - Generate test signals

2. **Test Other Pages**
   - Navigate to /market
   - Navigate to /portfolio
   - Navigate to /agents
   - Navigate to /strategy

3. **Test Real-time Updates**
   - Make changes in backend
   - Watch dashboard auto-refresh
   - Verify data updates

4. **Test WebSocket (if implemented)**
   - Connect WebSocket clients
   - Subscribe to market data
   - Receive real-time updates

## 📞 Still Having Issues?

If you're still experiencing connection problems:

1. **Verify both servers are running:**
   - Backend: `http://localhost:8000/health` should work
   - Frontend: `http://localhost:5188` should work

2. **Check firewall/antivirus:**
   - May be blocking localhost connections

3. **Try different ports:**
   - Backend: Try 8001, 8080
   - Frontend: Try 5189, 3000
   - Update `.env` accordingly

4. **Clear browser cache:**
   - Hard refresh: Ctrl+Shift+R
   - Clear site data in DevTools

5. **Check browser console for specific error messages**
   - Copy the full error
   - Search for the error online
   - Check if it's a CORS, network, or code issue
