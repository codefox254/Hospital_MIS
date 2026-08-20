import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { api, apiErrorMessage } from "../../lib/api";
import { useAuthStore } from "../../lib/auth-store";
import type { TokenPair } from "../../types/auth";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
  mfa_code: z.string().optional(),
});

type LoginForm = z.infer<typeof loginSchema>;

export function LoginPage() {
  const navigate = useNavigate();
  const setTokens = useAuthStore((s) => s.setTokens);
  const [serverError, setServerError] = useState<string | null>(null);
  const [needsMfa, setNeedsMfa] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  async function onSubmit(values: LoginForm) {
    setServerError(null);
    try {
      const { data } = await api.post<TokenPair>("/auth/token/", {
        email: values.email,
        password: values.password,
        mfa_code: values.mfa_code || undefined,
        client_type: "web",
      });
      setTokens(data);
      navigate("/", { replace: true });
    } catch (err) {
      const message = apiErrorMessage(err);
      if (message.toLowerCase().includes("mfa")) {
        setNeedsMfa(true);
      }
      setServerError(message);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={handleSubmit(onSubmit)} noValidate>
        <h1>FDO Hospital MIS</h1>
        <p className="login-subtitle">Staff sign in</p>

        <label htmlFor="email">Email</label>
        <input id="email" type="email" autoComplete="username" {...register("email")} />
        {errors.email && <p className="field-error">{errors.email.message}</p>}

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          {...register("password")}
        />
        {errors.password && <p className="field-error">{errors.password.message}</p>}

        {needsMfa && (
          <>
            <label htmlFor="mfa_code">MFA code</label>
            <input id="mfa_code" type="text" inputMode="numeric" {...register("mfa_code")} />
          </>
        )}

        {serverError && <p className="form-error">{serverError}</p>}

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
