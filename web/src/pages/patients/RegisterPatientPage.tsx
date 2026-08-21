import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";

import { apiErrorMessage } from "../../lib/api";
import { usePatients, useRegisterPatient } from "./hooks";

const schema = z.object({
  first_name: z.string().min(1, "First name is required."),
  last_name: z.string().min(1, "Last name is required."),
  date_of_birth: z.string().min(1, "Date of birth is required."),
  gender: z.enum(["male", "female", "other", "unspecified"]),
  national_id: z.string().optional(),
  phone: z.string().optional(),
  email: z.string().email("Enter a valid email.").optional().or(z.literal("")),
  blood_group: z.string().optional(),
  is_provisional: z.boolean().optional(),
});

type FormValues = z.infer<typeof schema>;

/** Reception's job is to find out whether this patient already has a
 * record here before creating a second one — a duplicate MRN for the
 * same person means their history (allergies, past visits, results)
 * splits across two records. This searches by whatever's been typed so
 * far (name, phone, national ID all hit the same backend search_fields)
 * and surfaces matches before the blank form is even filled in. */
function DuplicateCheck({ query }: { query: string }) {
  const { data, isFetching } = usePatients(query);
  const matches = data?.results ?? [];

  if (query.trim().length < 2) return null;

  return (
    <div className="form-panel" style={{ marginBottom: "1.25rem" }}>
      <h3>Existing patients matching &ldquo;{query}&rdquo;</h3>
      {isFetching && <p className="card-subtitle">Searching…</p>}
      {!isFetching && matches.length === 0 && (
        <p className="card-subtitle">No existing record found — safe to register as new.</p>
      )}
      {matches.length > 0 && (
        <div className="card-list">
          {matches.map((p) => (
            <Link key={p.id} to={`/patients/${p.id}`} className="modern-card clickable">
              <div className="icon-badge">👤</div>
              <div className="card-body">
                <p className="card-title">
                  {p.first_name} {p.last_name}
                </p>
                <p className="card-meta">
                  {p.mrn} · {p.phone || "no phone"} · DOB {p.date_of_birth}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function RegisterPatientPage() {
  const navigate = useNavigate();
  const register_ = useRegisterPatient();
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { gender: "unspecified" },
  });

  const [checkQuery, setCheckQuery] = useState("");
  const firstName = watch("first_name");
  const lastName = watch("last_name");
  const phone = watch("phone");

  async function onSubmit(values: FormValues) {
    try {
      const patient = await register_.mutateAsync(values);
      navigate(`/patients/${patient.id}`, { replace: true });
    } catch {
      // register_.error surfaces the message below; nothing further to do.
    }
  }

  return (
    <div>
      <h1>Register patient</h1>

      <DuplicateCheck query={checkQuery} />

      <form className="form-grid" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div>
          <label htmlFor="first_name">First name</label>
          <input
            id="first_name"
            {...register("first_name")}
            onBlur={() => setCheckQuery(phone || `${firstName ?? ""} ${lastName ?? ""}`.trim())}
          />
          {errors.first_name && <p className="field-error">{errors.first_name.message}</p>}
        </div>

        <div>
          <label htmlFor="last_name">Last name</label>
          <input
            id="last_name"
            {...register("last_name")}
            onBlur={() => setCheckQuery(phone || `${firstName ?? ""} ${lastName ?? ""}`.trim())}
          />
          {errors.last_name && <p className="field-error">{errors.last_name.message}</p>}
        </div>

        <div>
          <label htmlFor="date_of_birth">Date of birth</label>
          <input id="date_of_birth" type="date" {...register("date_of_birth")} />
          {errors.date_of_birth && <p className="field-error">{errors.date_of_birth.message}</p>}
        </div>

        <div>
          <label htmlFor="gender">Gender</label>
          <select id="gender" {...register("gender")}>
            <option value="unspecified">Unspecified</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div>
          <label htmlFor="national_id">National ID</label>
          <input id="national_id" {...register("national_id")} />
        </div>

        <div>
          <label htmlFor="phone">Phone</label>
          <input
            id="phone"
            {...register("phone")}
            onBlur={() => setCheckQuery(phone || `${firstName ?? ""} ${lastName ?? ""}`.trim())}
          />
        </div>

        <div>
          <label htmlFor="email">Email</label>
          <input id="email" type="email" {...register("email")} />
          {errors.email && <p className="field-error">{errors.email.message}</p>}
        </div>

        <div>
          <label htmlFor="blood_group">Blood group</label>
          <input id="blood_group" placeholder="e.g. O+" {...register("blood_group")} />
        </div>

        <label className="checkbox-row">
          <input type="checkbox" {...register("is_provisional")} />
          Provisional record (identity not yet fully verified)
        </label>

        {register_.isError && (
          <p className="form-error">{apiErrorMessage(register_.error)}</p>
        )}

        <button type="submit" disabled={isSubmitting} className="button-primary">
          {isSubmitting ? "Registering…" : "Register patient"}
        </button>
      </form>
    </div>
  );
}
