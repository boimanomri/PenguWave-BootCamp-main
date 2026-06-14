export interface SecurityEvent {
  id: string;
  timestamp: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  title: string;
  description: string;
  assetHostname: string;
  assetIp: string;
  sourceIp: string;
  tags: string[];
  userId: string;
}

export interface User {
  id: string;
  email: string;
  role: string;
  status: string;
  password: string;
}
