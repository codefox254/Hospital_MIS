export interface Facility {
  id: string;
  name: string;
  code: string;
}

export interface CurrentUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  facility: Facility;
  mfa_enabled: boolean;
  permissions: string[];
}

export interface TokenPair {
  access: string;
  refresh: string;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    fields?: Record<string, string[]>;
  };
}
