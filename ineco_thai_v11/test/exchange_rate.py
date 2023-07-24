import http.client
import requests


def test7():
    url = 'https://apigw1.bot.or.th/bot/public/Stat-ReferenceRate/v2/DAILY_REF_RATE/'
    querystring = {
        'start_period': '2020-10-09',
        'end_period': '2020-10-09'
    }
    headers = {
        'x-ibm-client-id': "65a82993-1e95-4ce8-81e3-5e8435529308",
        'accept': "application/json"
    }
    response = requests.request('GET', url, headers=headers, params=querystring)
    # print(response.text)


if __name__ == '__main__':
    test7()
