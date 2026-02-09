import requests

url = "https://api-uat-mobile-skyplus6e.goindigo.in/flightsearch/v1/flight/search"

headers = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "user_key": "2945e931b5e99bceed811fd202713432",
    "x-acf-sensor-data": "6,a,CTFQy+MyHDwvPKjyPz1dyxkZGg/tadL9bLYzWkTttUqVRo/RpmSgaiCSlaMHplO6r72BdakC56KbIXX2CqxuSfruob759H352r7aRzZYx9mULpNG+msxUNcQLa0robNX5wDXFYGruYkZFpI9aRF8e4aY68eVzEhq1CnIPAAyaIU=...",
    "source": "android",
    "version": "7.3.3",
    "user-agent": "IndiGoUAT/7.3.3.1 (Android 15; Build/AE3A.240806.036)",
    "authorization": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpYmUiLCJqdGkiOiJmZmU1ZTI2Yy1jNThlLTI0ZGYtZjdkOC01M2Y0MjZjMmU0NDEiLCJpc3MiOiJkb3RSRVogQVBJIn0.5PnJFN_jwB2VJSb9uj4_l2HiynVTco6AJV_2ewAIoKk"
}

raw_body = """
{
  "codes": {
    "currency": "INR",
    "vaxDoseNo": ""
  },
  "criteria": [
    {
      "dates": {
        "beginDate": "2026-01-30"
      },
      "flightFilters": {
        "type": "All"
      },
      "stations": {
        "originStationCodes": ["DEL"],
        "destinationStationCodes": ["BOM"],
        "originCityName": "Delhi",
        "destinationCityName": "Mumbai"
      }
    }
  ],
  "passengers": {
    "residentCountry": "IN",
    "types": [
      {
        "count": 1,
        "discountCode": "",
        "type": "ADT"
      }
    ]
  },
  "infantCount": 0,
  "taxesAndFees": "TaxesAndFees",
  "totalPassengerCount": 1,
  "searchType": "OneWay",
  "extraSeat": {
    "adultDoubleSeat": 0,
    "adultTripleSeat": 0,
    "seniorCitizenDoubleSeat": 0,
    "seniorCtizenTripleSeat": 0,
    "childrenDoubleSeat": 0,
    "childrenTripleSeat": 0
  },
  "isRedeemTransaction": false,
  "adobeData": {
    "product": {
      "productInfo": {
        "payType": "Cash",
        "tripType": "OneWay",
        "sector": "DEL-BOM",
        "departureDates": "08-01-2026",
        "daysUntilDeparture": 1,
        "currencyCode": "INR",
        "specialFare": "",
        "paxInfo": "1|1|0|0|0",
        "doubleSeatSelected": 0,
        "tripleSeatSelected": 0,
        "bookingPurpose": "",
        "promotionalCode": "",
        "marketType": "Domestic",
        "productViewed": {
          "Flights": "1"
        }
      }
    },
    "loyalty": {
      "pointsEarn": "1",
      "pointsBurn": "0",
      "balance": "0"
    }
  }
}
"""

response = requests.post(url, data=raw_body, headers=headers)

print(response.status_code)
print(response.text)