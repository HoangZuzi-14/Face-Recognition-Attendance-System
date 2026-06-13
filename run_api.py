import uvicorn
import os

if __name__ == "__main__":
    # Đảm bảo thư mục logs được tạo
    os.makedirs("logs", exist_ok=True)
    
    print("Starting FastAPI Server at http://127.0.0.1:8000")
    print("API docs available at http://127.0.0.1:8000/docs")
    
    uvicorn.run("app.api:app", host="127.0.0.1", port=8000, reload=True)
