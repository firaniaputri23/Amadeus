# SendGrid Webhook Microservice

This microservice provides webhook endpoints to receive and process inbound emails from SendGrid's inbound parser.

## Overview

SendGrid's inbound parser allows you to receive emails at your domain and have them parsed and sent to your webhook endpoint as HTTP POST requests. This microservice provides simple endpoints to handle these webhooks.

## Endpoints

### 1. Main Webhook Endpoint
- **URL**: `/sendgrid/webhook`
- **Method**: `POST`
- **Purpose**: Receives and logs parsed email data from SendGrid
- **Response**: JSON with processing status

### 2. Test Endpoint
- **URL**: `/sendgrid/webhook/test`
- **Method**: `GET`
- **Purpose**: Test if the webhook endpoint is accessible
- **Response**: JSON confirmation

### 3. Simple Webhook Endpoint
- **URL**: `/sendgrid/webhook/simple`
- **Method**: `POST`
- **Purpose**: Ultra-simple endpoint that just returns 200 OK
- **Response**: Basic JSON acknowledgment

## Setup Instructions

### 1. Configure SendGrid Inbound Parser

1. Log in to your SendGrid account
2. Go to Settings > Inbound Parse
3. Add a new host & URL:
   - **Hostname**: Your domain (e.g., `mail.yourdomain.com`)
   - **URL**: `https://yourdomain.com/sendgrid/webhook`
   - **Spam Check**: Enable if desired
   - **Send Raw**: Enable if you need the raw email

### 2. DNS Configuration

Add an MX record to your domain:
```
Type: MX
Host: mail (or your chosen subdomain)
Value: mx.sendgrid.net
Priority: 10
```

### 3. Test the Setup

1. Send an email to `test@mail.yourdomain.com`
2. Check your application logs to see the parsed email data
3. Or use the test endpoint: `GET /sendgrid/webhook/test`

## Webhook Data

SendGrid sends the following data (among others):

- `from`: Sender email address
- `to`: Recipient email address
- `subject`: Email subject
- `text`: Plain text body
- `html`: HTML body
- `cc`: CC recipients
- `attachments`: File attachments (if any)
- `dkim`: DKIM validation result
- `spf`: SPF validation result

## Logging

The webhook logs all received emails with:
- Timestamp
- Sender and recipient
- Subject line
- Body length (text/HTML)
- All form fields for debugging

## Security Considerations

For production use, consider adding:
- Webhook signature verification
- Rate limiting
- Input validation
- Authentication/authorization
- HTTPS enforcement

## Example Usage

```bash
# Test the webhook endpoint
curl -X GET https://yourdomain.com/sendgrid/webhook/test

# Send test data to webhook (for testing)
curl -X POST https://yourdomain.com/sendgrid/webhook \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "from=test@example.com&to=recipient@yourdomain.com&subject=Test&text=Hello World"
```

## Troubleshooting

1. **Webhook not receiving data**: Check DNS MX record and SendGrid configuration
2. **500 errors**: Check application logs for detailed error messages
3. **Missing data**: Verify SendGrid inbound parser settings
4. **Authentication issues**: Ensure the webhook endpoint is publicly accessible

## Next Steps

To extend this webhook:
1. Add email storage to database
2. Implement email processing logic
3. Add attachment handling
4. Set up email forwarding
5. Add webhook signature verification