export interface TokenPair {
  access: string;
  refresh: string;
}

export interface CurrentUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  facility: {
    id: string;
    name: string;
    code: string;
  };
  mfa_enabled: boolean;
  permissions: string[];
}

export interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
    fields?: Record<string, string[]>;
  };
}
