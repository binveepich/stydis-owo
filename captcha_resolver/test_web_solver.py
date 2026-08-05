#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script cho WebSolver
Dùng để kiểm tra web_solver.py có hoạt động với OwO Bot không
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Thêm đường dẫn để import web_solver
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_solver import WebSolver


class MockBot:
    """Mock bot để test, chỉ có log và token"""
    def __init__(self, token):
        self.token = token
        self.username = "TestBot"
        self.user = type('obj', (object,), {'id': '123456789'})()
    
    def log(self, level: str, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            'INFO': '\033[94m',
            'SUCCESS': '\033[92m',
            'WARN': '\033[93m',
            'ERROR': '\033[91m',
            'RESET': '\033[0m'
        }
        color = colors.get(level, colors['RESET'])
        print(f"[{timestamp}] {color}[{level}]{colors['RESET']} {msg}")


async def test_websolver():
    """Hàm test chính"""
    print("=" * 60)
    print("🧪 TEST WEBSOLVER - OwO Bot Captcha")
    print("=" * 60)
    print()
    
    # 1. Nhập thông tin
    print("📝 Nhập thông tin cấu hình:")
    print("-" * 40)
    
    discord_token = input("🔑 Discord Token: ").strip()
    if not discord_token:
        print("❌ Token Discord không được để trống!")
        return
    
    api_key = input("🔑 API Key (2Captcha/YesCaptcha): ").strip()
    if not api_key:
        print("❌ API Key không được để trống!")
        return
    
    print("\n[1] Chọn service:")
    print("   1. 2Captcha")
    print("   2. YesCaptcha")
    service_choice = input("Chọn (1/2): ").strip()
    
    service = "2captcha" if service_choice == "1" else "yescaptcha"
    print(f"✅ Đã chọn service: {service}")
    
    retries = input("\n[2] Số lần thử lại (mặc định: 3): ").strip()
    retries = int(retries) if retries.isdigit() else 3
    
    print("\n" + "=" * 60)
    print("🚀 BẮT ĐẦU TEST...")
    print("=" * 60 + "\n")
    
    # 2. Tạo mock bot và solver
    mock_bot = MockBot(discord_token)
    solver = WebSolver(
        api_key=api_key,
        service=service,
        bot=mock_bot
    )
    
    # 3. Kiểm tra balance
    print("[1] 🔍 Kiểm tra số dư API...")
    balance = await solver.get_balance()
    
    if balance <= 0:
        print(f"⚠️ Số dư: ${balance:.4f} (Có thể API key không hợp lệ hoặc hết tiền)")
        confirm = input("\n❓ Vẫn tiếp tục? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ Đã hủy test.")
            return
    else:
        print(f"✅ Số dư: ${balance:.4f}")
    
    # 4. Chạy solve
    print("\n[2] 🔐 Bắt đầu giải captcha...")
    print("   (Quá trình này có thể mất 30-90 giây)")
    print("   Vui lòng đợi...\n")
    
    try:
        start_time = datetime.now()
        result = await solver.solve(discord_token, retries=retries)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 60)
        print("📊 KẾT QUẢ TEST")
        print("=" * 60)
        print(f"⏱️  Thời gian: {duration:.1f} giây")
        print(f"📌 Kết quả: {'✅ THÀNH CÔNG' if result else '❌ THẤT BẠI'}")
        
        if result:
            print("\n🎉 Captcha đã được giải và xác minh thành công!")
            print("   Bot của bạn đã vượt qua captcha thành công.")
        else:
            print("\n⚠️ Captcha KHÔNG được giải.")
            print("   Nguyên nhân có thể:")
            print("   - API key không hợp lệ hoặc hết tiền")
            print("   - Token Discord không đúng hoặc hết hạn")
            print("   - OwO Bot đã thay đổi cấu trúc captcha")
            print("   - Kết nối mạng bị chặn")
            
    except Exception as e:
        print(f"\n❌ LỖI: {e}")
        import traceback
        traceback.print_exc()


def load_config_from_file():
    """Đọc config từ file settings.json nếu có"""
    config_file = "settings.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get('token', ''), config.get('captcha', {}).get('api_key', '')
        except:
            pass
    return '', ''


async def main():
    """Main entry point"""
    # Kiểm tra nếu có file settings.json
    discord_token, api_key = load_config_from_file()
    
    if discord_token and api_key:
        print("📂 Phát hiện file settings.json")
        print(f"   Token: {discord_token[:20]}...{discord_token[-5:]}")
        print(f"   API Key: {api_key[:10]}...{api_key[-5:]}")
        use_config = input("\n❓ Sử dụng config này? (y/n): ").strip().lower()
        if use_config == 'y':
            # Chạy test với config
            print("\n🚀 Bắt đầu test với config...")
            
            # Tạo mock bot
            mock_bot = MockBot(discord_token)
            solver = WebSolver(
                api_key=api_key,
                service="2captcha",
                bot=mock_bot
            )
            
            # Kiểm tra balance
            balance = await solver.get_balance()
            print(f"💰 Số dư: ${balance:.4f}")
            
            if balance > 0:
                result = await solver.solve(discord_token, retries=3)
                print(f"\n📌 Kết quả: {'✅ THÀNH CÔNG' if result else '❌ THẤT BẠI'}")
            else:
                print("❌ Số dư không đủ hoặc API key không hợp lệ.")
            return
    
    # Nếu không có config hoặc không muốn dùng, chạy test tương tác
    await test_websolver()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️ Đã dừng test.")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()