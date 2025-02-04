url: https://jsonplaceholder.typicode.com
paths:
  /posts/{postId}/comments:
    get:
      summary: Get comments for a specific post
      parameters:
        - name: postId
          in: path
          required: true
          description: ID of the post to fetch comments for
          schema:
            type: integer
      responses:
        '200':
          description: A list of comments
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    postId:
                      type: integer
                      example: 1
                    id:
                      type: integer
                      example: 1
                    name:
                      type: string
                      example: "id labore ex et quam laborum"
                    email:
                      type: string
                      example: "Eliseo@gardner.biz"
                    body:
                      type: string
                      example: "laudantium enim quasi est quidem magnam voluptate ipsam eos"
