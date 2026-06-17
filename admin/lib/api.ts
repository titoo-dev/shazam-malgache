// Client API minimal vers le backend (chemins relatifs proxifiés par Next).

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parse<T>(res: Response): Promise<T> {
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail =
      (data && (data.detail || data.message)) || res.statusText || "erreur";
    throw new ApiError(res.status, String(detail));
  }
  return data as T;
}

export const fetcher = <T>(url: string): Promise<T> =>
  fetch(url).then((r) => parse<T>(r));

export async function post<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parse<T>(res);
}

export async function patch<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parse<T>(res);
}

export async function del<T>(url: string): Promise<T> {
  const res = await fetch(url, { method: "DELETE" });
  return parse<T>(res);
}

export async function postForm<T>(url: string, form: FormData): Promise<T> {
  const res = await fetch(url, { method: "POST", body: form });
  return parse<T>(res);
}
