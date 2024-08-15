import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

URL = 'https://a.com'
KEY = 'sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
MAX_WORKERS = 2

RED = "\033[91m"
GREEN = "\033[92m"
ORANGE = "\033[38;5;208m"
RESET = "\033[0m"


def fetch_models(url, headers):
    """获取模型列表"""
    try:
        response = requests.get(f"{url}/v1/models", headers=headers)
        response.raise_for_status()  # 检查请求是否成功
        return response.json().get('data', [])
    except requests.RequestException as e:
        print(f"Failed to get models: {e}")
        return []


def check_model(model, url, headers, data):
    """检查单个模型的可用性并计算延迟"""
    try:
        data['model'] = model  # 确保在请求中包含模型 ID
        start_time = time.time()  # 记录开始时间
        response = requests.post(f"{url}/v1/chat/completions", headers=headers, json=data)
        response.raise_for_status()  # 检查请求是否成功
        latency = time.time() - start_time  # 计算延迟
        response_data = response.json()
        if 'error' in response_data:  # 根据实际 API 响应结构检查错误
            return model, False, response_data['error'], latency
        return model, True, None, latency  # 模型状态正常
    except requests.RequestException as e:
        return model, False, str(e), None


def display_result(model, is_available, error, latency):
    """显示检查结果"""
    if is_available:
        if latency < 4:
            color = GREEN
        elif latency < 6:
            color = ORANGE
        else:
            color = RED
        print(f"{color}[{latency:.2f}s]{RESET} {model}")
    else:
        print(f"{RED}[X]{RESET} {model} - {RED}{error or 'Unknown error'}{RESET}")


def check_models_concurrently(models, url, headers, data, max_workers=1):
    """并行检查多个模型的可用性"""
    check_passes = []  # 用于存放可用模型的数组
    check_failed = []  # 用于存放失效模型的数组

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_model, model, url, headers, data): model for model in models}
        for future in as_completed(futures):
            model, is_available, error, latency = future.result()
            display_result(model, is_available, error, latency)
            (check_passes if is_available else check_failed).append(model)

    return check_passes, check_failed


def main():
    base_url = URL
    headers = {
        'Authorization': 'Bearer ' + KEY,
        'Content-Type': 'application/json'
    }
    data = {
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1
    }

    models = fetch_models(base_url, headers)
    model_ids = [model['id'] for model in models]  # 获取模型 ID 列表

    print('Start checking...')
    print('------------------')

    start_time = time.time()  # 记录开始时间

    available_models, failed_models = check_models_concurrently(model_ids, base_url, headers, data, MAX_WORKERS)

    end_time = time.time()  # 记录结束时间
    total_time = end_time - start_time  # 计算并输出总用时

    # print('End of inspection!')
    print('------------------')
    print(f'Available：{len(available_models)}')
    print(f'Failed：{len(failed_models)}')
    print(f"Total time: {total_time:.2f}s")
    print('------------------')
    print('Available models: ')
    print(', '.join(available_models))


if __name__ == "__main__":
    main()
