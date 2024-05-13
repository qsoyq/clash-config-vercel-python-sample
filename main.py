from flask import Flask, request, Response
import requests
import yaml
import os
import json
import re

# 在 Vercel 项目中添加环境变量，名称为 SUB_URLS ，值为列表形式，如：["sub_0", "sub_1"]，注意：列表内的订阅地址必须用双引号包裹。
proxy_provider_sub_urls = json.loads(os.getenv('SUB_URLS'))

# 在 Vercel 项目中添加环境变量，名称为 UUID_PASSKEY，值为任意，生成的订阅链接必须带此参数对应的路径才会返回正确的订阅值。可使用 https://www.uuidgenerator.net/ 在线生成。
uuid_passkey = os.getenv('UUID_PASSKEY')

proxy_provider_proxies = []
filter_regex = ''

for proxy_provider_sub_url in proxy_provider_sub_urls:
    headers = {'User-Agent': 'clash'}
    response = requests.get(proxy_provider_sub_url, headers=headers)

    sub = response.text
    sub_obj = yaml.safe_load(sub)
    proxies = sub_obj.get('proxies', [])
    proxies = [x for x in proxies if x.get("name") and re.match(filter_regex, x['name'])]
    filtered_proxies = [proxy for proxy in proxies]
    # filtered_proxies = [proxy for proxy in proxies if 'plugin' not in proxy] # why?

    proxy_provider_proxies.extend(filtered_proxies)

if len(proxy_provider_proxies) == 0:
    raise Exception('未在订阅中找到节点信息')

# 此处填写你的落地机相关信息，后续 proxy-groups 中需要对应此处的 name 。
proxies = [{
        'name': '落地机',
        'type': 'ss',
        'server': 'your_ss_server_ip',
        'port': 1366,
        'cipher': 'chacha20-ietf-poly1305',
        'password': 'your_ss_server_password',
        'udp': True
        },
    ]
proxies = proxy_provider_proxies + proxies

# 以下 config 中的各项内容自行修改填写，我的比较简单。主要修改 mixed-port、dns、rules、proxy-groups 段。
# 唯一需要注意的是，这是 Python 字典，不是 .yaml 文件，注意写法区别，例如某个元素的值是数字或者 True/False 的话，需要不带引号，文本则需要带引号。
config = {
    'ipv6': False,
    'mixed-port': 7890,
    'allow-lan': True,
    'bind-address': '*',
    'log-level': 'info',
    'external-controller': '0.0.0.0:9090',
    'dns': {
        'enable': True,
        'ipv6': False,
        'default-nameserver': ['223.5.5.5', '119.29.29.29'],
        'enhanced-mode': 'fake-ip',
        'fake-ip-range': '198.18.0.1/16',
        'nameserver': ['https://1.1.1.1/dns-query',] # dns 服务器可自行修改或添加，我用的是自建的，参考：https://rethinkdns.com/。
    },
    'rules': [
        'DOMAIN-SUFFIX,local,DIRECT',
        'IP-CIDR,127.0.0.0/8,DIRECT',
        'IP-CIDR,172.16.0.0/12,DIRECT',
        'IP-CIDR,192.168.0.0/16,DIRECT',
        'IP-CIDR,10.0.0.0/8,DIRECT',
        'IP-CIDR,100.64.0.0/10,DIRECT',
        'MATCH, 🌏 Relay'],
    'proxies': proxies,
    'proxy-groups': [
        {
            'name': '🌏 Relay',
            'type': 'relay',
            "proxies": ['✈️ 机场', '落地机']
        },
        {
            'name': '✈️ 机场',
            'type': 'select',
            "proxies": ['🚀 最快节点(自动)'] + [proxy['name'] for proxy in proxy_provider_proxies]
        },
        {
            'name': '🚀 最快节点(自动)',
            'type': 'url-test', # 我是根据 url-test 测速，如果喜欢手动，这一整段也可以改成手动或者负载均衡模式。
            'exclude-filter': '(?i)IEPL|IPLC', # 这里我删除了 IPLC、IEPL 等高倍率节点，富哥可以删除本行。也可以根据需要添加。
            'url': 'https://www.gstatic.com/generate_204',
            'interval': 300,
            'proxies' : [proxy['name'] for proxy in proxy_provider_proxies]
        }
    ],
}


app = Flask(__name__)


fake_response_text = 'Hello, world.'

@app.route('/')
def index():
    return Response(fake_response_text, mimetype='text/plain')


@app.route('/<uuid>')
def usualexplosion(uuid):
    user_agent = request.headers.get('User-Agent', '').lower()
    if uuid == uuid_passkey: # 判断 UUID_PASSKEY 是否匹配，防止被很容易地找到订阅地址。
        if 'clash' in user_agent or 'shadowrocket' in user_agent: # 防止被浏览器直接请求。使用 Clash for Windows、Stash、Mihomo 等客户端会自动在请求时携带包含 clash 文本的 User-Agent。如果你用的客户端，发起请求时不包括 clash 或者 shadowrocket 的 User-Agent，则需要自行添加或删除本判断。
            return Response(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), mimetype='text/plain')
    return Response(fake_response_text, mimetype='text/plain')
