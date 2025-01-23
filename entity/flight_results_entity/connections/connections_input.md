curl https://airportgap.com/api/airports
Example of successful response Status: 200 OK

{
  "data": [{
      "attributes": {
        "altitude": 5282,
        "city": "Goroka",
        "country": "Papua New Guinea",
        "iata": "GKA",
        "icao": "AYGA",
        "latitude": "-6.08169",
        "longitude": "145.391998",
        "name": "Goroka Airport",
        "timezone": "Pacific/Port_Moresby"

      },
      "id": "GKA",
      "type": "airport"
    },
    {
      "attributes": {
        "altitude": 20,
        "city": "Madang",
        "country": "Papua New Guinea",
        "iata": "MAG",
        "icao": "AYMD",
        "latitude": "-5.20708",
        "longitude": "145.789001",
        "name": "Madang Airport",
        "timezone": "Pacific/Port_Moresby"
      },
      "id": "MAG",
      "type": "airport"
    },

    ...

    {
      "attributes": {
        "altitude": 1343,
        "city": "Brandon",
        "country": "Canada",
        "iata": "YBR",
        "icao": "CYBR",
        "latitude": "49.91",
        "longitude": "-99.951897",
        "name": "Brandon Municipal Airport",
        "timezone": "America/Winnipeg"
      },
      "id": "YBR",
      "type": "airport"
    },
    {
      "attributes": {
        "altitude": 90,
        "city": "Cambridge Bay",
        "country": "Canada",
        "iata": "YCB",
        "icao": "CYCB",
        "latitude": "69.108101",
        "longitude": "-105.138",
        "name": "Cambridge Bay Airport",
        "timezone": "America/Edmonton"
      },
      "id": "YCB",
      "type": "airport"
    }
  ],
  "links": {
    "first": "https://airportgap.com/api/airports",
    "last": "https://airportgap.com/api/airports?page=203",
    "next": "https://airportgap.com/api/airports?page=2",
    "prev": "https://airportgap.com/api/airports",
    "self": "https://airportgap.com/api/airports"
  }
}
