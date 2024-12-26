import requests
import json
import subprocess
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Cloudflare API Token
API_TOKEN = ''  # 替换为你的 API Token

# Cloudflare API 请求头
headers = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json',
}


# 生成 SPF 记录
def generate_spf(domain, ip):
    return generate_txt_record(f"v=spf1 ip4:{ip} ~all")


# 生成 DKIM 公钥和私钥
def generate_dkim_keys(domain, private_key_path):
    selector = f"dkim-{domain.split('.')[0]}"  # 使用域名前缀加 "dkim-" 作为 selector
    public_key_path = None  # 不保存公钥到文件

    private_key_dir = os.path.dirname(private_key_path)
    if not os.path.exists(private_key_dir):
        os.makedirs(private_key_dir)

    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "RSA", "-out", private_key_path, "-pkeyopt", "rsa_keygen_bits:2048"])

    public_key_command = f"openssl rsa -in {private_key_path} -pubout"
    public_key = subprocess.check_output(public_key_command, shell=True).decode('utf-8')

    public_key = public_key.replace("-----BEGIN PUBLIC KEY-----", "").replace("-----END PUBLIC KEY-----", "").replace(
        "\n", "")

    dkim_record = f"v=DKIM1; k=rsa; p={public_key}"
    dkim_record_with_quotes = generate_txt_record(dkim_record)

    return selector, dkim_record_with_quotes


# 生成 DMARC 记录
def generate_dmarc(domain):
    return generate_txt_record(
        f"v=DMARC1; p=quarantine; rua=mailto:dmarc-reports@{domain}; ruf=mailto:dmarc-reports@{domain}")


# 生成 MX 记录
def generate_mx(domain):
    return {
        "value": f"mail.{domain}"
    }


# 生成 A 记录
def generate_a(domain, ip):
    return ip


# 生成 TXT 记录并加引号
def generate_txt_record(content):
    return f'"{content}"'


# 生成 _adsp 记录
def generate_adsp(domain):
    return generate_txt_record(f"dkim=all")  # 强制要求所有邮件必须进行 DKIM 签名


# 检查 mail 子域是否解析成功
def check_mail_subdomain_resolution(domain, attempt=1):
    dns_servers = ["8.8.8.8", "8.8.4.4", "1.1.1.1"]  # 使用 3 个 DNS 服务器进行查询
    success = False

    for server in dns_servers:
        try:
            response = subprocess.check_output(["nslookup", f"mail.{domain}", server], stderr=subprocess.STDOUT)
            output = response.decode('utf-8')

            # 检查 nslookup 输出是否包含 IP 地址（即解析成功）
            if "NXDOMAIN" in output:
                print(f"警告: mail.{domain} 在 {server} 上未解析成功。")
            elif "Name:" in output and "Address:" in output:
                print(f"成功: mail.{domain} 在 {server} 上解析成功。")
                success = True
                break  # 如果成功则停止查询
            else:
                print(f"警告: mail.{domain} 子域在 {server} 上解析结果异常。输出:\n{output}")
        except subprocess.CalledProcessError as e:
            print(f"错误: 检查 mail.{domain} 在 {server} 上解析失败。")

    return success


# 生成并添加 DNS 记录
def generate_and_add_dns_records(domain, ip):
    zone_id = get_zone_id(domain)
    if not zone_id:
        return  # 如果获取 Zone ID 失败，跳过当前域名

    # 1. 添加主域名的 A 记录
    a_record = generate_a(domain, ip)
    #    print(f"上传 A 记录: {domain}, 内容: {a_record}")
    add_dns_record(zone_id, 'A', domain, a_record)

    # 2. 添加 mail 子域的 A 记录
    mail_a_record = generate_a(domain, ip)
    #    print(f"上传 mail 子域 A 记录: mail.{domain}, 内容: {mail_a_record}")
    add_dns_record(zone_id, 'A', 'mail', mail_a_record)

    # 3. 立即上传 SPF、DKIM、DMARC 和 _adsp 记录
    spf_record = generate_spf(domain, ip)
    add_dns_record(zone_id, 'TXT', domain, spf_record)

    private_key_path = f"/etc/pmta/DomainKeys/{domain}_private.key"
    selector, dkim_record = generate_dkim_keys(domain, private_key_path)
    add_dns_record(zone_id, 'TXT', f"{selector}._domainkey.{domain}", dkim_record)

    dmarc_record = generate_dmarc(domain)
    add_dns_record(zone_id, 'TXT', f"_dmarc.{domain}", dmarc_record)

    # 上传 _adsp 记录
    adsp_record = generate_adsp(domain)
    add_dns_record(zone_id, 'TXT', f"_adsp.{domain}", adsp_record)

    # 4. 定期检查 mail 子域的解析状态
    mail_resolved = False
    attempt = 1
    while not mail_resolved:
        mail_resolved = check_mail_subdomain_resolution(domain, attempt)
        if not mail_resolved:
            print(f"mail.{domain} 解析未生效，{attempt * 5}秒后重新检查...")
            time.sleep(attempt * 5)  # 每次增加等待时间，逐步增加检查间隔
            attempt += 1  # 增加尝试次数

    # 5. 最后上传 MX 记录
    mx_record = generate_mx(domain)
    #    print(f"上传 MX 记录: {domain}, 内容: {mx_record}")
    add_dns_record(zone_id, 'MX', domain, mx_record, priority=10)


# 添加 DNS 记录到 Cloudflare，默认不开启代理
def add_dns_record(zone_id, record_type, name, content, ttl=3600, priority=None, proxied=False):
    data = {
        'type': record_type,
        'name': name,
        'ttl': ttl,
        'proxied': proxied  # 禁用代理
    }

    if record_type == 'MX':
        data['content'] = content['value']  # 提取 `value` 属性
        if priority:
            data['priority'] = priority
    else:
        data['content'] = content

    url = f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records'
    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        print(f"成功添加 {record_type} 记录: {name}")
    else:
        print(f"添加 {record_type} 记录失败: {name}")
        print(f"响应: {response.json()}")


def delete_dns_record(domain, domain_ip, postmaster, mail_ip, account):
    zone_id = get_zone_id(domain, API_TOKEN)
    if not zone_id:
        return  # 如果获取 Zone ID 失败，跳过当前域名
        # 删除 A 记录、MX 记录、TXT 记录等
    record_types = ['A', 'MX', 'TXT']
    for record_type in record_types:
        url = f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type={record_type}'
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            records = response.json()['result']
            for record in records:
                record_id = record['id']
                delete_url = f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}'
                delete_response = requests.put(delete_url, headers=headers)
                if delete_response.status_code == 200:
                    print(f"成功删除 {record_type} 记录: {record['name']}")
                else:
                    print(f"删除 {record_type} 记录失败: {record['name']}")
        else:
            print(f"获取 {record_type} 记录失败，状态码: {response.status_code}")


# 主函数：使用线程池并行处理所有域名
def main():
    domains = read_domains("../domains.txt")
    for domain in domains:
        print(domain, "test")
    operation = input("请选择操作: 1 - 添加解析, 2 - 删除解析, 3 - 开启所有 A 记录代理, 4 - 关闭所有 A 记录代理: ")
    record_choice = input("请选择所有域名的解析记录应用于主域名还是子域名:\n1 - 主域名\n2 - 子域名\n请输入 1 或 2: ")
    # 设置最大线程数，根据 Cloudflare API 的请求限制进行调整
    max_threads = 50  # 最大线程数可以根据需要调整
    match operation:
        # 添加解析操作
        case "2":
            with ThreadPoolExecutor(max_threads) as executor:
                # 提交每个域名的 DNS 记录处理任务
                futures = [executor.submit(generate_and_add_dns_records, domain, ip) for domain, ip in domains.items()]
                # 等待任务完成并收集结果
                for future in as_completed(futures):
                    try:
                        future.result()  # 可能会抛出异常，这里捕获
                    except Exception as e:
                        print(f"处理域名时发生错误: {e}")
        case "2":
            return "Not found"
        case "3":
            return "I'm a teapot"
        case _:
            return "Something's wrong with the internet"

    with ThreadPoolExecutor(max_threads) as executor:
        # 提交每个域名的 DNS 记录处理任务
        futures = [executor.submit(generate_and_add_dns_records, domain, ip) for domain, ip in domains.items()]

        # 等待任务完成并收集结果
        for future in as_completed(futures):
            try:
                future.result()  # 可能会抛出异常，这里捕获
            except Exception as e:
                print(f"处理域名时发生错误: {e}")


# 获取域名对应的 Zone ID
def get_zone_id(domain):
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


# 读取域名和对应的 IP 地址
def read_domains(file_path):
    domains = {}
    with open(file_path, 'r') as f:
        for line in f:
            domain, ip = line.strip().split(':')
            domains[domain] = ip
    return domains


if __name__ == "__main__":
    main()
