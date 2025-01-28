1. Collect Books

GET
​/api​/v1​/Books
Parameters
Cancel
No parameters

Execute
Clear
Responses
Curl

curl -X GET "https://fakerestapi.azurewebsites.net/api/v1/Books" -H  "accept: text/plain; v=1.0"
Request URL
https://fakerestapi.azurewebsites.net/api/v1/Books
Server response
Code	Details
200	

Response headers
 api-supported-versions: 1.0 
 content-type: application/json; charset=utf-8; v=1.0 
 date: Tue28 Jan 2025 15:29:23 GMT 
 server: Kestrel 
 transfer-encoding: chunked 
Responses
Code	Description	Links
200	
Success

Media type

text/plain; v=1.0
Controls Accept header.
Example Value
Schema
[
  {
    "id": 0,
    "title": "string",
    "description": "string",
    "pageCount": 0,
    "excerpt": "string",
    "publishDate": "2025-01-28T15:31:14.813Z"
  }
]


2. For each book get its cover url

   GET
​/api​/v1​/CoverPhotos​/books​/covers​/{idBook}
Parameters
Cancel
Name	Description
idBook *
integer($int32)
(path)
2
Execute
Clear
Responses
Curl

curl -X GET "https://fakerestapi.azurewebsites.net/api/v1/CoverPhotos/books/covers/2" -H  "accept: text/plain; v=1.0"
Request URL
https://fakerestapi.azurewebsites.net/api/v1/CoverPhotos/books/covers/2
Server response
Code	Details
200	
Response body
Download
[
  {
    "id": 2,
    "idBook": 2,
    "url": "https://placeholdit.imgix.net/~text?txtsize=33&txt=Book 2&w=250&h=350"
  }
]
Response headers
 api-supported-versions: 1.0 
 content-type: application/json; charset=utf-8; v=1.0 
 date: Tue28 Jan 2025 15:31:12 GMT 
 server: Kestrel 
 transfer-encoding: chunked 
