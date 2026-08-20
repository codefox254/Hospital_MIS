import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { apiErrorMessage } from "../../lib/api";
import { useRegisterPatient } from "./hooks";

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

export function RegisterPatientPage() {
  const navigate = useNavigate();
  const register_ = useRegisterPatient();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { gender: "unspecified" },
  });

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
      <form className="form-grid" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div>
          <label htmlFor="first_name">First name</label>
          <input id="first_name" {...register("first_name")} />
          {errors.first_name && <p className="field-error">{errors.first_name.message}</p>}
        </div>

        <div>
          <label htmlFor="last_name">Last name</label>
          <input id="last_name" {...register("last_name")} />
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
          <input id="phone" {...register("phone")} />
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

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Registering…" : "Register patient"}
        </button>
      </form>
    </div>
  );
}
