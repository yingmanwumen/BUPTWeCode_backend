from common.wxdecrypt.WXBizDataCrypt import WXBizDataCrypt

def main():
    appId = 'wx4f4bc4dec97d474b'
    sessionKey = 'tiihtNczf5v6AKRyjwEUhQ=='
    encryptedData = 'CiyLU1Aw2KjvrjMdj8YKliAjtP4gsMZMQmRzooG2xrDcvSnxIMXFufNstNGTyaGS9uT5geRa0W4oTOb1WT7fJlAC+oNPdbB+3hVbJSRgv+4lGOETKUQz6OYStslQ142dNCuabNPGBzlooOmB231qMM85d2/fV6ChevvXvQP8Hkue1poOFtnEtpyxVLW1zAo6/1Xx1COxFvrc2d7UL/lmHInNlxuacJXwu0fjpXfz/YqYzBIBzD6WUfTIF9GRHpOn/Hz7saL8xz+W//FRAUid1OksQaQx4CMs8LOddcQhULW4ucetDf96JcR3g0gfRK4PC7E/r7Z6xNrXd2UIeorGj5Ef7b1pJAYB6Y5anaHqZ9J6nKEBvB4DnNLIVWSgARns/8wR2SiRS7MNACwTyrGvt9ts8p12PKFdlqYTopNHR1Vf7XjfhQlVsAJdNiKdYmYVoKlaRv85IfVunYzO0IKXsyl7JCUjCpoG20f0a04COwfneQAGGwd5oa+T8yO5hzuyDb/XcxxmK01EpqOyuxINew=='
    iv = 'r7BXXKkLb8qrSNn05n0qiA=='
    # encryptedData = "Us6zL5F9Dvq8AzrK1OK0qFIhHfJATTDNFvscYQKE2nyQzOwsIOIuwlNTSwuo3xrfhLQo6tOBbV/huwLyyTFxKxJgg8FXkwONtzSeVQhkMgIlgBhhgz8InjBwuZn5ItJx1cvuClNgl/64KTFplMqdy4lGYG7gG8BsPdhRbsmlO2HV0DxS7njiMgRYWOAhb0lxf8xgmN9bbIYzbhgW9w85Jabw6JpEos9Qb2ZcOWztHTLtJMbR9cARU5LoyCmXXNAJqjqXw30Jnpuipl83u3nhxGdm/5gHcfeuu3vrUuUuv8lwd3G0ny2hBC45r5/Dkhq/MkEs67JmDC9l74G1F+Qv5kRJCzipUoeveBxnPWeBgkfqV6FxMxxWj0ZR0gJNUZDKRlKJ0naUcZ0nMWHaLKsoDrs7x/8qqZJ5gGjBpnBxRltWte1lEh7eetd/0xJbOPvbGgG3B5nuVoowPqPRMpOIzA=="
    # sessionKey = "yTilHDEc5kWjAx2Q2sGDOg=="
    # iv = "wEeXfpFOVqHbH1tdVV2twA=="

    pc = WXBizDataCrypt(appId, sessionKey)

    print(pc.decrypt(encryptedData, iv))

if __name__ == '__main__':
    main()