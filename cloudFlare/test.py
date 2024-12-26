import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# Cloudflare API Token 和账户对应字典
API_TOKENS = {
    "":""
    # 添加更多账户和 API Token 绑定
}

def read_domains(file_path,record_choice):
    domains = []
    with open(file_path, 'r') as f:
        for line in f:
            try:
                # 根据 "：" 分割成五个部分
                domain, domain_ip, postmaster, mail_ip, account = line.strip().split(':')
                if record_choice == '1':
                    parts = domain.split('.')
                    if len(parts) == 3:  # 判断域名被点分割后是否有四个部分，即包含三个点的情况
                        domain=domain.split('.', 1)[-1] if '.' in domain else domain
                        print("ddd",domain)
                domains.append({
                    "domain": domain,
                    "domain_ip": domain_ip,  # 用于 A 记录
                    "postmaster": postmaster,  # 用于 MX 记录
                    "mail_ip": mail_ip,  # 用于 mail 记录
                    "account": account,  # 用于选择 API Token
                })
            except ValueError:
                print(f"警告: 无法解析此行，格式不正确：{line.strip()}")  # 处理格式错误的行
    return domains




# 删除 DNS 记录
def deleted_dns_records(domain, domain_ip,postmaster,mail_ip,account):
    api_token = API_TOKENS.get(account)
    if not api_token:
        print(f"错误: 未找到账户 {domain['account']} 对应的 API Token。")
        return
    zone_id = get_zone_id(api_token,domain)
    if not zone_id:
        return  # 如果获取 Zone ID 失败，跳过当前域名
    record_types = ['A', 'MX', 'TXT']
    for record_type in record_types:
        url = f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type={record_type}'
        response = requests.get(url, headers={'Authorization': f'Bearer {api_token}','Content-Type': 'application/json',})
        # 打印响应的原始内容
        if response.status_code == 200:
            records = response.json()['result']
            for record in records:
                record_id = record['id']
                delete_url = f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}'
                delete_response = requests.delete(delete_url, headers={'Authorization': f'Bearer {api_token}','Content-Type': 'application/json',})
                if delete_response.status_code == 200:
                    print(f"成功删除 {record_type} 记录: {record['name']}")
                else:
                    print(f"删除 {record_type} 记录失败: {record['name']}")
        else:
            print(f"获取 {record_type} 记录失败，状态码: {response.status_code}")

def put_dns_records(domain, domain_ip,postmaster,mail_ip,account,bool):
    api_token = API_TOKENS.get(account)
    if not api_token:
        print(f"错误: 未找到账户 {domain['account']} 对应的 API Token。")
        return
    zone_id = get_zone_id(api_token, domain)
    if not zone_id:
        return  # 如果获取 Zone ID 失败，跳过当前域名
    record_types = ['A']
    for record_type in record_types:
        url = f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type={record_type}'
        response = requests.get(url,headers={'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json', })
        for res in response.json()['result']:
            data={  "comment":res["comment"] ,  "content": res["content"],  "name": res["name"],  "proxied": bool, "ttl": res["ttl"],  "type": res["type"]}
            url1 = f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{res["id"]}'
            try:
                response = requests.put(url1, headers={'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json', }, data=json.dumps(data))
                if response.status_code == 200:
                    print("更新DNS记录成功")
                else:
                    print(f"更新DNS记录失败，状态码: {response.status_code}")
            except requests.RequestException as e:
                print(f"请求发生异常: {e}")


# 获取域名对应的 Zone ID
def get_zone_id(api_token,domain):
    # Cloudflare API 请求头
    headers = {'Authorization': f'Bearer {api_token}','Content-Type': 'application/json'}
    url = f'https://api.cloudflare.com/client/v4/zones?name={domain}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        zone_data = response.json()
        if zone_data['success'] and len(zone_data['result']) > 0:
            return zone_data['result'][0]['id']
        else:
            print(f"错误: 找不到域名 {domain} 的 Zone ID。")
            return None
    else:
        print(f"API 请求失败，状态码 {response.status_code}: {response.text}")
        return None


def main():
    operation = input("请选择操作:  2 - 删除解析, 3 - 开启所有 A 记录代理, 4 - 关闭所有 A 记录代理: ")
    # record_choice = input("请选择所有域名的解析记录应用于主域名还是子域名:\n1 - 主域名\n2 - 子域名\n请输入 1 或 2: ")
    domains = read_domains("./domains.txt","2")
    for domain in domains:
        print(domain)
    match operation:
        #添加解析操作
        case "2":
            # 创造线程池并发
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(deleted_dns_records,
                                           domain['domain'],
                                           domain['domain_ip'],
                                           domain['postmaster'],
                                           domain['mail_ip'],
                                           domain['account']
                                           ) for domain in domains]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"添加域名处理域名时发生错误: {e}")
        case "3":
            # 创造线程池并发
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(put_dns_records,
                                           domain['domain'],
                                           domain['domain_ip'],
                                           domain['postmaster'],
                                           domain['mail_ip'],
                                           domain['account'],
                                           True
                                           ) for domain in domains]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"添加域名处理域名时发生错误: {e}")
        case "4":
            # 创造线程池并发
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(put_dns_records,
                                           domain['domain'],
                                           domain['domain_ip'],
                                           domain['postmaster'],
                                           domain['mail_ip'],
                                           domain['account'],
                                           False
                                           ) for domain in domains]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"添加域名处理域名时发生错误: {e}")
        case _:
            return "Something's wrong with the internet"

if __name__ == "__main__":
    main()