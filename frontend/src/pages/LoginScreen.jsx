import { useMemo, useRef, useState } from "react";
import { AlertCircle, CheckCircle2, Eye, EyeOff, LoaderCircle, Wallet } from "lucide-react";
import spendsyLogo from "../assets/logo.svg";
import { APP_VERSION } from "@shared/config/constants";
import { authApi } from "../api";

const SUBMIT_LOCK_MS = 1000;
const MAX_AUTH_ERROR_LENGTH = 180;

const passwordChecks = [
  { id: "length", label: "8+ chars", test: (value) => value.length >= 8 },
  { id: "upper", label: "Uppercase", test: (value) => /[A-Z]/.test(value) },
  { id: "lower", label: "Lowercase", test: (value) => /[a-z]/.test(value) },
  { id: "digit", label: "Number", test: (value) => /\d/.test(value) },
];

function cleanErrorMessage(err, isSignup) {
  const fallback = isSignup
    ? "Registration failed. Please check your details."
    : "Incorrect username or password.";
  const raw =
    err?.body?.detail ||
    err?.body?.message ||
    (typeof err?.message === "string" ? err.message : "") ||
    fallback;

  return String(raw)
    .replace(/[<>]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, MAX_AUTH_ERROR_LENGTH);
}

const LoginScreen = ({ onAuthSuccess, showToast }) => {
  // Local state for the form
  const [mode, setMode] = useState("login");
  const isSignup = mode === "signup";
  const [authData, setAuthData] = useState({
    username: "",
    password: "",
    email: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const lastSubmitAt = useRef(0);

  const passwordScore = useMemo(
    () => passwordChecks.filter((check) => check.test(authData.password)).length,
    [authData.password],
  );

  const updateField = (field, value) => {
    setAuthData((current) => ({ ...current, [field]: value }));
    setFieldErrors((current) => {
      if (!current[field]) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
  };

  const validateForm = () => {
    const nextErrors = {};
    const username = authData.username.trim();
    const email = authData.email.trim();

    if (!username || username.length < 3) {
      nextErrors.username = "Enter at least 3 characters.";
    }

    if (mode === "forgot") {
      setFieldErrors(nextErrors);
      return Object.keys(nextErrors).length === 0;
    }

    if (isSignup && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      nextErrors.email = "Enter a valid email address.";
    }

    if (!authData.password) {
      nextErrors.password = "Enter your password.";
    } else if (isSignup && passwordScore < passwordChecks.length) {
      nextErrors.password = "Use a stronger password.";
    }

    if (isSignup && !acceptedTerms) {
      nextErrors.terms = "Please accept the terms.";
    }

    setFieldErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleAuth = async (e) => {
    e.preventDefault();

    const now = Date.now();
    if (isSubmitting || now - lastSubmitAt.current < SUBMIT_LOCK_MS) {
      return;
    }

    if (!validateForm()) {
      return;
    }

    if (mode === "forgot") {
      lastSubmitAt.current = now;
      setIsSubmitting(true);
      try {
        setErrorMessage("");
        await new Promise((r) => setTimeout(r, 800)); // Simulate API call
        showToast("If an account exists, a reset link has been sent to your email.", "success");
        setMode("login");
      } catch (err) {
        setErrorMessage("Failed to send reset link.");
      } finally {
        setIsSubmitting(false);
      }
      return;
    }

    lastSubmitAt.current = now;
    setIsSubmitting(true);

    try {
      setErrorMessage("");
      const trimmedUsername = authData.username.trim();
      const trimmedEmail = authData.email.trim();
      const requestBody = {
        username: trimmedUsername,
        password: authData.password,
        email: trimmedEmail || undefined,
      };
      const data = isSignup
        ? await authApi.register(requestBody)
        : await authApi.login(requestBody);

      // Support both microservices auth ({ user, tokens }) and Django auth ({ data: { user_id, token, ... } })
      const payload = data?.data ?? data;
      const user = payload?.user ?? payload ?? {};
      const tokens = payload?.tokens ?? {};
      const accessToken =
        tokens?.access_token ||
        payload?.token ||
        payload?.access_token ||
        "";
      onAuthSuccess({
        id: user.id || payload.user_id,
        username: user.username || payload.username || trimmedUsername,
        email: user.email || payload.email || trimmedEmail,
        created_at: user.created_at || user.createdAt || payload.created_at || payload.date_joined,
        token: accessToken,
      });
      showToast(
        isSignup ? "Account created! Please check your email to verify your account." : `Logged in as ${user.username || trimmedUsername}`,
        "success",
      );
    } catch (err) {
      if (err.body) {
        const finalMessage = cleanErrorMessage(err, isSignup);

        setErrorMessage(finalMessage);
        showToast(finalMessage, "error");
      } else {
        setErrorMessage("Backend unreachable. Please try again.");
        showToast("Backend unreachable", "error");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleMode = () => {
    setMode((current) => (current === "login" ? "signup" : "login"));
    setErrorMessage("");
    setFieldErrors({});
  };

  const clearSiteData = () => {
    try {
      window.localStorage?.clear();
      window.sessionStorage?.clear();
    } catch {
      showToast("Could not clear browser storage in this mode.", "error");
      return;
    }
    window.location.href = window.location.pathname;
  };

  return (
    <div className="min-h-screen w-full bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-blue-900 via-slate-900 to-black text-white flex flex-col items-center justify-center p-6">
      <div className="z-10 w-full max-w-sm text-center">
 <div className="w-20 h-20 bg-gradient-to-tr from-blue-500 to-cyan-400 rounded-3xl mx-auto mb-6 flex items-center justify-center transform rotate-6 border border-white/10 shadow-2xl">          <Wallet className="w-10 h-10 text-white" />        </div>

        <h1 className="text-4xl font-black tracking-[0.1em] bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-cyan-400 to-blue-400 animate-gradient-x mb-2">
          Spendsy
        </h1>
        <p className="text-blue-200/50 mb-8 text-sm font-medium tracking-wide uppercase">
          Financial clarity for the modern era.
        </p>

        <div className="bg-white/5 border border-white/10 p-6 rounded-2xl backdrop-blur-xl text-left">
          <h2 className="text-xl font-bold mb-4">
            {mode === "forgot"
              ? "Reset Password"
              : isSignup
              ? "Create Account"
              : "Login"}
          </h2>

          {errorMessage && (
            <div
              className="mb-3 flex gap-2 rounded-xl border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-200"
              role="alert"
            >
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleAuth} className="flex flex-col gap-3" noValidate>
            <div>
              <label htmlFor="auth-username" className="mb-1 block text-xs font-semibold text-blue-100">
                Username
              </label>
              <input
                id="auth-username"
                value={authData.username}
                placeholder="Username"
                className="w-full bg-black/20 border border-white/10 p-3 rounded-xl focus:border-blue-500 outline-none text-sm"
                required
                autoComplete="username"
                aria-invalid={Boolean(fieldErrors.username)}
                aria-describedby={fieldErrors.username ? "auth-username-error" : undefined}
                onChange={(e) => updateField("username", e.target.value)}
              />
              {fieldErrors.username && (
                <p id="auth-username-error" className="mt-1 text-xs text-red-200">
                  {fieldErrors.username}
                </p>
              )}
            </div>
            {isSignup && (
              <div>
                <label htmlFor="auth-email" className="mb-1 block text-xs font-semibold text-blue-100">
                  Email
                </label>
                <input
                  id="auth-email"
                  value={authData.email}
                  placeholder="Email"
                  className="w-full bg-black/20 border border-white/10 p-3 rounded-xl focus:border-blue-500 outline-none text-sm"
                  type="email"
                  required
                  autoComplete="email"
                  aria-invalid={Boolean(fieldErrors.email)}
                  aria-describedby={fieldErrors.email ? "auth-email-error" : undefined}
                  onChange={(e) => updateField("email", e.target.value)}
                />
                {fieldErrors.email && (
                  <p id="auth-email-error" className="mt-1 text-xs text-red-200">
                    {fieldErrors.email}
                  </p>
                )}
              </div>
            )}
            {mode !== "forgot" && (
              <div>
                <label htmlFor="auth-password" className="mb-1 block text-xs font-semibold text-blue-100">
                  Password
                </label>
                <div className="relative">
                <input
                  id="auth-password"
                  value={authData.password}
                  type={showPassword ? "text" : "password"}
                  placeholder="Password"
                  className="w-full bg-black/20 border border-white/10 p-3 pr-10 rounded-xl focus:border-blue-500 outline-none text-sm"
                  required
                  autoComplete={isSignup ? "new-password" : "current-password"}
                  aria-invalid={Boolean(fieldErrors.password)}
                  aria-describedby={fieldErrors.password ? "auth-password-error" : undefined}
                  onChange={(e) => updateField("password", e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute inset-y-0 right-2 flex items-center text-slate-400 hover:text-white"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
              {fieldErrors.password && (
                <p id="auth-password-error" className="mt-1 text-xs text-red-200">
                  {fieldErrors.password}
                </p>
              )}
              {isSignup && (
                <div className="mt-2 grid grid-cols-2 gap-1 text-[11px] text-slate-300">
                  {passwordChecks.map((check) => {
                    const passed = check.test(authData.password);
                    return (
                      <span key={check.id} className="flex items-center gap-1">
                        <CheckCircle2
                          className={passed ? "h-3 w-3 text-emerald-300" : "h-3 w-3 text-slate-600"}
                          aria-hidden="true"
                        />
                        {check.label}
                      </span>
                    );
                  })}
                </div>
              )}
              {isSignup && (
                <div className="mt-4 flex items-start gap-2 group cursor-pointer" onClick={() => setAcceptedTerms(!acceptedTerms)}>
                  <div className={`mt-0.5 w-4 h-4 rounded border flex items-center justify-center transition-colors ${acceptedTerms ? 'bg-blue-600 border-blue-500' : 'border-white/20 group-hover:border-white/40'}`}>
                    {acceptedTerms && <CheckCircle2 className="w-3 h-3 text-white" />}
                  </div>
                  <p className="text-[10px] text-slate-400 leading-tight">
                    I agree to the <span className="text-blue-400 hover:underline">Terms of Service</span> and <span className="text-blue-400 hover:underline">Privacy Policy</span>.
                  </p>
                </div>
              )}
              {isSignup && fieldErrors.terms && (
                <p className="mt-1 text-xs text-red-200">
                  {fieldErrors.terms}
                </p>
              )}
            </div>
            )}
            <button
              className="mt-2 flex items-center justify-center gap-2 rounded-xl bg-blue-600 py-3 font-bold shadow-lg shadow-blue-900/20 transition-all hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isSubmitting}
            >
              {isSubmitting && <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />}
              {isSubmitting
                ? "Please wait"
                : mode === "forgot"
                ? "Send Reset Link"
                : isSignup
                ? "Sign Up"
                : "Sign In"}
            </button>
          </form>

          <button
            onClick={toggleMode}
            className="mt-4 text-xs opacity-60 hover:opacity-100 transition-opacity w-full text-center"
          >
            {mode === "forgot"
              ? "Back to Login"
              : isSignup
              ? "Already have an account? Login"
              : "Need an account? Create one"}
          </button>

          {mode === "login" && (
            <button
              type="button"
              onClick={() => {
                setMode("forgot");
                setErrorMessage("");
                setFieldErrors({});
              }}
              className="mt-3 text-xs text-blue-200/70 hover:text-blue-100 transition-colors w-full text-center"
            >
              Forgot password?
            </button>
          )}
        </div>

        <div className="mt-8 flex flex-col items-center gap-2">
          <div className="text-[10px] text-slate-500 font-mono uppercase tracking-widest">
            {APP_VERSION}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginScreen;
