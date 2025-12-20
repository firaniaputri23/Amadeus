import { SendGridService } from '../services/sendgrid.js';
import { SendGridContact, SendGridTemplate, SendGridSingleSend } from '../types/index.js';

export const getToolDefinitions = (service: SendGridService) => [
  {
    name: 'delete_contacts',
    description: 'Delete contacts from your SendGrid account',
    inputSchema: {
      type: 'object',
      properties: {
        emails: {
          type: 'array',
          items: {
            type: 'string'
          },
          description: 'Array of email addresses to delete'
        }
      },
      required: ['emails']
    }
  },
  {
    name: 'list_contacts',
    description: 'List all contacts in your SendGrid account',
    inputSchema: {
      type: 'object',
      properties: {},
      required: []
    }
  },
  {
    name: 'send_email',
    description: 'Send an email using SendGrid',
    inputSchema: {
      type: 'object',
      properties: {
        to: {
          type: 'string',
          description: 'Recipient email address'
        },
        subject: {
          type: 'string',
          description: 'Email subject line'
        },
        text: {
          type: 'string',
          description: 'Plain text content of the email'
        },
        html: {
          type: 'string',
          description: 'HTML content of the email (optional)'
        },
        from: {
          type: 'string',
          description: 'Sender email address (must be verified with SendGrid)'
        },
        template_id: {
          type: 'string',
          description: 'SendGrid template ID (optional)'
        },
        dynamic_template_data: {
          type: 'object',
          description: 'Dynamic data for template variables (optional)'
        }
      },
      required: ['to', 'subject', 'text', 'from']
    }
  },
  {
    name: 'add_contact',
    description: 'Add a contact to your SendGrid marketing contacts',
    inputSchema: {
      type: 'object',
      properties: {
        email: {
          type: 'string',
          description: 'Contact email address'
        },
        first_name: {
          type: 'string',
          description: 'Contact first name (optional)'
        },
        last_name: {
          type: 'string',
          description: 'Contact last name (optional)'
        },
        custom_fields: {
          type: 'object',
          description: 'Custom field values (optional)'
        }
      },
      required: ['email']
    }
  },
  {
    name: 'create_contact_list',
    description: 'Create a new contact list in SendGrid',
    inputSchema: {
      type: 'object',
      properties: {
        name: {
          type: 'string',
          description: 'Name of the contact list'
        }
      },
      required: ['name']
    }
  },
  {
    name: 'add_contacts_to_list',
    description: 'Add contacts to an existing SendGrid list',
    inputSchema: {
      type: 'object',
      properties: {
        list_id: {
          type: 'string',
          description: 'ID of the contact list'
        },
        emails: {
          type: 'array',
          items: {
            type: 'string'
          },
          description: 'Array of email addresses to add to the list'
        }
      },
      required: ['list_id', 'emails']
    }
  },
  {
    name: 'create_template',
    description: 'Create a new email template in SendGrid',
    inputSchema: {
      type: 'object',
      properties: {
        name: {
          type: 'string',
          description: 'Name of the template'
        },
        subject: {
          type: 'string',
          description: 'Default subject line for the template'
        },
        html_content: {
          type: 'string',
          description: 'HTML content of the template'
        },
        plain_content: {
          type: 'string',
          description: 'Plain text content of the template'
        }
      },
      required: ['name', 'subject', 'html_content', 'plain_content']
    }
  },
  {
    name: 'get_template',
    description: 'Retrieve a SendGrid template by ID',
    inputSchema: {
      type: 'object',
      properties: {
        template_id: {
          type: 'string',
          description: 'ID of the template to retrieve'
        }
      },
      required: ['template_id']
    }
  },
  {
    name: 'delete_template',
    description: 'Delete a dynamic template from SendGrid',
    inputSchema: {
      type: 'object',
      properties: {
        template_id: {
          type: 'string',
          description: 'ID of the template to delete'
        }
      },
      required: ['template_id']
    }
  },
  {
    name: 'validate_email',
    description: 'Validate an email address using SendGrid',
    inputSchema: {
      type: 'object',
      properties: {
        email: {
          type: 'string',
          description: 'Email address to validate'
        }
      },
      required: ['email']
    }
  },
  {
    name: 'get_stats',
    description: 'Get SendGrid email statistics',
    inputSchema: {
      type: 'object',
      properties: {
        start_date: {
          type: 'string',
          description: 'Start date in YYYY-MM-DD format'
        },
        end_date: {
          type: 'string',
          description: 'End date in YYYY-MM-DD format (optional)'
        },
        aggregated_by: {
          type: 'string',
          enum: ['day', 'week', 'month'],
          description: 'How to aggregate the statistics (optional)'
        }
      },
      required: ['start_date']
    }
  },
  {
    name: 'list_templates',
    description: 'List all email templates in your SendGrid account',
    inputSchema: {
      type: 'object',
      properties: {},
      required: []
    }
  },
  {
    name: 'delete_list',
    description: 'Delete a contact list from SendGrid',
    inputSchema: {
      type: 'object',
      properties: {
        list_id: {
          type: 'string',
          description: 'ID of the contact list to delete'
        }
      },
      required: ['list_id']
    }
  },
  {
    name: 'list_contact_lists',
    description: 'List all contact lists in your SendGrid account',
    inputSchema: {
      type: 'object',
      properties: {},
      required: []
    }
  },
  {
    name: 'get_contacts_by_list',
    description: 'Get all contacts in a SendGrid list',
    inputSchema: {
      type: 'object',
      properties: {
        list_id: {
          type: 'string',
          description: 'ID of the contact list'
        }
      },
      required: ['list_id']
    }
  },
  {
    name: 'list_verified_senders',
    description: 'List all verified sender identities in your SendGrid account',
    inputSchema: {
      type: 'object',
      properties: {},
      required: []
    }
  },
  {
    name: 'list_suppression_groups',
    description: 'List all unsubscribe groups in your SendGrid account',
    inputSchema: {
      type: 'object',
      properties: {},
      required: []
    }
  },
  {
    name: 'send_to_list',
    description: 'Send an email to a contact list using SendGrid Single Sends',
    inputSchema: {
      type: 'object',
      properties: {
        name: {
          type: 'string',
          description: 'Name of the single send'
        },
        list_ids: {
          type: 'array',
          items: {
            type: 'string'
          },
          description: 'Array of list IDs to send to'
        },
        subject: {
          type: 'string',
          description: 'Email subject line'
        },
        html_content: {
          type: 'string',
          description: 'HTML content of the email'
        },
        plain_content: {
          type: 'string',
          description: 'Plain text content of the email'
        },
        sender_id: {
          type: 'number',
          description: 'ID of the verified sender'
        },
        suppression_group_id: {
          type: 'number',
          description: 'ID of the suppression group for unsubscribes (required if custom_unsubscribe_url not provided)'
        },
        custom_unsubscribe_url: {
          type: 'string',
          description: 'Custom URL for unsubscribes (required if suppression_group_id not provided)'
        }
      },
      required: ['name', 'list_ids', 'subject', 'html_content', 'plain_content', 'sender_id']
    }
  },
  {
    name: 'get_single_send',
    description: 'Get details of a specific single send',
    inputSchema: {
      type: 'object',
      properties: {
        single_send_id: {
          type: 'string',
          description: 'ID of the single send to retrieve'
        }
      },
      required: ['single_send_id']
    }
  },
  {
    name: 'list_single_sends',
    description: 'List all single sends in your SendGrid account',
    inputSchema: {
      type: 'object',
      properties: {},
      required: []
    }
  },
  {
    name: 'remove_contacts_from_list',
    description: 'Remove contacts from a SendGrid list without deleting them',
    inputSchema: {
      type: 'object',
      properties: {
        list_id: {
          type: 'string',
          description: 'ID of the contact list'
        },
        emails: {
          type: 'array',
          items: {
            type: 'string'
          },
          description: 'Array of email addresses to remove from the list'
        }
      },
      required: ['list_id', 'emails']
    }
  }
];

export const handleToolCall = async (service: SendGridService, name: string, args: any) => {
  switch (name) {
    case 'delete_contacts':
      await service.deleteContactsByEmails(args.emails);
      return { content: [{ type: 'text', text: `Successfully deleted ${args.emails.length} contacts` }] };

    case 'list_contacts':
      const allContacts = await service.listAllContacts();
      return {
        content: [{
          type: 'text',
          text: JSON.stringify(allContacts.map(c => ({
            email: c.email,
            first_name: c.first_name,
            last_name: c.last_name
          })), null, 2)
        }]
      };

    case 'send_email':
      await service.sendEmail(args);
      return { content: [{ type: 'text', text: `Email sent successfully to ${args.to}` }] };

    case 'add_contact':
      await service.addContact(args as SendGridContact);
      return { content: [{ type: 'text', text: `Contact ${args.email} added successfully` }] };

    case 'create_contact_list':
      const list = await service.createList(args.name);
      return { content: [{ type: 'text', text: `Contact list "${args.name}" created with ID: ${list.id}` }] };

    case 'add_contacts_to_list':
      await service.addContactsToList(args.list_id, args.emails);
      return { content: [{ type: 'text', text: `Added ${args.emails.length} contacts to list ${args.list_id}` }] };

    case 'create_template':
      const template = await service.createTemplate(args);
      return { content: [{ type: 'text', text: `Template "${args.name}" created with ID: ${template.id}` }] };

    case 'get_template':
      const retrievedTemplate = await service.getTemplate(args.template_id);
      return { content: [{ type: 'text', text: JSON.stringify(retrievedTemplate, null, 2) }] };

    case 'delete_template':
      await service.deleteTemplate(args.template_id);
      return { content: [{ type: 'text', text: `Template ${args.template_id} deleted successfully` }] };

    case 'validate_email':
      const validation = await service.validateEmail(args.email);
      return { content: [{ type: 'text', text: JSON.stringify(validation, null, 2) }] };

    case 'get_stats':
      const stats = await service.getStats(args);
      return { content: [{ type: 'text', text: JSON.stringify(stats, null, 2) }] };

    case 'list_templates':
      const templates = await service.listTemplates();
      return {
        content: [{
          type: 'text',
          text: JSON.stringify(templates.map(t => ({
            id: t.id,
            name: t.name,
            generation: t.generation,
            updated_at: t.updated_at,
            versions: t.versions.length
          })), null, 2)
        }]
      };

    case 'delete_list':
      await service.deleteList(args.list_id);
      return { content: [{ type: 'text', text: `Contact list ${args.list_id} deleted successfully` }] };

    case 'list_contact_lists':
      const lists = await service.listContactLists();
      return {
        content: [{
          type: 'text',
          text: JSON.stringify(lists.map(l => ({
            id: l.id,
            name: l.name,
            contact_count: l.contact_count
          })), null, 2)
        }]
      };

    case 'get_contacts_by_list':
      const contacts = await service.getContactsByList(args.list_id);
      return {
        content: [{
          type: 'text',
          text: JSON.stringify(contacts.map(c => ({
            email: c.email,
            first_name: c.first_name,
            last_name: c.last_name
          })), null, 2)
        }]
      };

    case 'list_verified_senders':
      const senders = await service.getVerifiedSenders();
      return {
        content: [{
          type: 'text',
          text: JSON.stringify(senders, null, 2)
        }]
      };

    case 'list_suppression_groups':
      const groups = await service.getSuppressionGroups();
      return {
        content: [{
          type: 'text',
          text: JSON.stringify(groups, null, 2)
        }]
      };

    case 'send_to_list':
      if (!args.suppression_group_id && !args.custom_unsubscribe_url) {
        throw new Error('Either suppression_group_id or custom_unsubscribe_url must be provided');
      }

      const newSingleSend = await service.createSingleSend({
        name: args.name,
        send_to: {
          list_ids: args.list_ids
        },
        email_config: {
          subject: args.subject,
          html_content: args.html_content,
          plain_content: args.plain_content,
          sender_id: args.sender_id,
          suppression_group_id: args.suppression_group_id,
          custom_unsubscribe_url: args.custom_unsubscribe_url
        }
      });
      
      // Schedule it to send immediately
      await service.scheduleSingleSend(newSingleSend.id, 'now');
      
      return {
        content: [{
          type: 'text',
          text: `Email "${args.name}" has been sent to the specified lists`
        }]
      };

    case 'get_single_send':
      const retrievedSingleSend = await service.getSingleSend(args.single_send_id);
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            id: retrievedSingleSend.id,
            name: retrievedSingleSend.name,
            status: retrievedSingleSend.status,
            send_at: retrievedSingleSend.send_at,
            list_ids: retrievedSingleSend.send_to.list_ids
          }, null, 2)
        }]
      };

    case 'list_single_sends':
      const allSingleSends = await service.listSingleSends();
      return {
        content: [{
          type: 'text',
          text: JSON.stringify(allSingleSends.map((s: SendGridSingleSend) => ({
            id: s.id,
            name: s.name,
            status: s.status,
            send_at: s.send_at
          })), null, 2)
        }]
      };

    case 'remove_contacts_from_list':
      await service.removeContactsFromList(args.list_id, args.emails);
      return { content: [{ type: 'text', text: `Removed ${args.emails.length} contacts from list ${args.list_id}` }] };

    default:
      throw new Error(`Unknown tool: ${name}`);
  }
};
