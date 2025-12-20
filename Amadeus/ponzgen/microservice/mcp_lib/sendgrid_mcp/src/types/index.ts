// Common interfaces for SendGrid API responses and requests

export interface SendGridContact {
  id?: string;
  email: string;
  first_name?: string;
  last_name?: string;
  custom_fields?: Record<string, any>;
}

export interface SendGridList {
  id: string;
  name: string;
  contact_count: number;
}

export interface SendGridTemplate {
  id: string;
  name: string;
  generation: string;
  updated_at: string;
  versions: SendGridTemplateVersion[];
}

export interface SendGridTemplateVersion {
  id: string;
  template_id: string;
  active: number;
  name: string;
  html_content: string;
  plain_content: string;
  subject: string;
}

export interface SendGridStats extends Array<{
  date: string;
  stats: Array<{
    metrics: {
      opens: number;
      clicks: number;
      bounces: number;
      spam_reports: number;
      unique_opens: number;
      unique_clicks: number;
      blocks: number;
      delivered: number;
      bounce_drops?: number;
      deferred?: number;
      invalid_emails?: number;
      processed?: number;
      requests?: number;
      spam_report_drops?: number;
      unsubscribe_drops?: number;
      unsubscribes?: number;
    };
  }>;
}> {}

export interface SendGridSingleSend {
  id: string;
  name: string;
  status: 'draft' | 'scheduled' | 'triggered' | 'canceled';
  categories?: string[];
  send_at?: string;
  send_to: {
    list_ids: string[];
  };
  email_config: {
    subject: string;
    html_content: string;
    plain_content: string;
    sender_id: number;
    suppression_group_id?: number;
    custom_unsubscribe_url?: string;
  };
}
