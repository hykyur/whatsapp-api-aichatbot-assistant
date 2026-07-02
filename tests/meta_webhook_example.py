import requests

url = "http://127.0.0.1:5000/whatsapp/webhook"

data = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "419561257915477",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550783881",
                            "phone_number_id": "106540352242922"
                        },
                        "contacts": [
                            {
                                "profile": {
                                    "name": "Sheena Nelson"
                                },
                                "wa_id": "16505551234"
                            }
                        ],
                        "messages": [
                            {
                                "from": "16505551234",
                                "id": "wamid.HBgLMTY1MDM4Nzk0MzkVAgASGBQzQTRBNjU5OUFFRTAzODEwMTQ0RgA=",
                                "timestamp": "1749416383",
                                "type": "text",
                                "text": {
                                    "body": "Does it come in another color?"
                                }
                            }
                        ]
                    },
                    "field": "messages"
                }
            ]
        }
    ]
}

headers = {
    "Authorization": "Bearer <Token>",
    "Content-Type": "application/json"
}


response = requests.request("POST", url, json=data, headers=headers)

print(response.json())