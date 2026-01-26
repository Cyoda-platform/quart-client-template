# Basic Newsletter — Weekly Cat Fact

## Overview
A simple weekly cat-fact email newsletter that retrieves a random cat fact from the Cat Fact API and sends it to all subscribers every week.

## Functional Requirements
- Schedule a weekly job to fetch a random cat fact from https://catfact.ninja and store it as the week's content.
- Allow users to sign up with their email address via a simple signup form or API endpoint.
- Store subscriber email addresses in a subscribers table.
- Provide an unsubscribe link in every email to remove an email from the subscribers list.
- Send the fetched cat fact to all subscribers via email once a week.
- Log successful sends and failures for reporting.

## Non-functional Requirements
- Keep data retention minimal: store subscriber email and subscription timestamp.
- Ensure email sending handles retries and records failures.
- Application should be deployable using the Cyoda build flow.

## Reporting
- Weekly report: number of subscribers, number of emails sent, number of failures.
