import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

URL = 'https://api.openai.com'
KEY = 'sk-'
MAX_WORKERS = 2

RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"


def fetch_models(url, headers):
    """获取模型列表"""
    response = requests.get(url + '/v1/models', headers=headers)
    if response.status_code == 200:
        return response.json()['data']
    else:
        print('Failed to get models: ', response.status_code)
        return []


def check_model(model, url, headers, data):
    """检查单个模型的可用性"""
    try:
        data['model'] = model  # 确保在请求中包含模型 ID
        response = requests.post(url + '/v1/chat/completions', headers=headers, json=data)
        response.raise_for_status()  # 如果响应状态码不是 200，将引发异常

        response_data = response.json()
        if 'error' in response_data:  # 根据实际 API 响应结构检查错误
            return model, False, response_data['error']
        else:
            return model, True, None  # 模型状态正常
    except requests.exceptions.HTTPError as http_err:
        return model, False, str(http_err)
    except requests.exceptions.RequestException as req_err:
        return model, False, str(req_err)


def check_models_concurrently(models, url, headers, data, max_workers=2):
    """并行检查多个模型的可用性"""
    check_passes = []  # 用于存放可用模型的数组
    check_failed = []  # 用于存放失效模型的数组

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_model = {executor.submit(check_model, model, url, headers, data): model for model in models}

        for future in as_completed(future_to_model):
            model, is_available, error = future.result()
            if is_available:
                check_passes.append(model)
                print(f"{GREEN}[√]{RESET} {model}")
            else:
                print(f"{RED}[X]{RESET} {model} - {RED}{error or 'Unknown error'}{RESET}")

    return check_passes, check_failed


def main():
    base_url = URL
    headers = {
        'Authorization': 'Bearer ' + KEY,
        'Content-Type': 'application/json'
    }

    data = {
        "messages": [
            {"role": "user", "content": "hi"}
        ],
    }  # 你的请求数据

    models = fetch_models(base_url, headers)
    model_ids = [model['id'] for model in models]  # 获取模型 ID 列表

    print('Start checking...')
    print('-----------------')

    available_models, failed_models = check_models_concurrently(model_ids, base_url, headers, data, MAX_WORKERS)

    print('End of inspection!')
    print('------------------')
    output = ", ".join(available_models)
    print(output)

    # print("Available models:", available_models)
    # print("Failed models:", failed_models)


if __name__ == "__main__":
    main()
