import { useState } from 'react';
import { motion } from 'motion/react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { ArrowLeft, Phone, Lock, Send } from 'lucide-react';
import { api } from '../api';
import { toast } from 'sonner';

interface AuthScreenProps {
  role: 'buyer' | 'seller';
  onComplete: (isGuest?: boolean, accessToken?: string) => void;
  onBack: () => void;
}

export function AuthScreen({ role, onComplete, onBack }: AuthScreenProps) {
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login');

  // Login State
  const [loginPhone, setLoginPhone] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Register State
  const [registerStep, setRegisterStep] = useState<'phone' | 'otp'>('phone');
  const [registerPhone, setRegisterPhone] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [telegramUsername, setTelegramUsername] = useState('');
  const [registerCode, setRegisterCode] = useState('');

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loginPhone && password) {
      setIsLoading(true);
      try {
        const data = await api.login(loginPhone, password);
        toast.success('Login successful');
        onComplete(false, data.access_token);
      } catch (error) {
        toast.error('Login failed. Please check your credentials.');
        console.error(error);
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleRegisterPhoneSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (registerPhone.length > 5 && registerPassword.length >= 6 && telegramUsername.length > 1) {
      setIsLoading(true);
      try {
        await api.requestTelegramOtp(telegramUsername);
        toast.success('Code sent to your Telegram!');
        setRegisterStep('otp');
      } catch (error: any) {
        toast.error(error.message || 'Failed to send OTP');
      } finally {
        setIsLoading(false);
      }
    } else {
      toast.error('Please fill in all fields (password min 6 chars)');
    }
  };

  const handleRegisterOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (registerCode.length === 6) {
      setIsLoading(true);
      try {
        // Verify OTP first
        await api.verifyTelegramOtp(telegramUsername, registerCode);

        // Register user
        await api.register({
          phone: registerPhone,
          password: registerPassword,
          role: role
        });

        // Auto login
        const data = await api.login(registerPhone, registerPassword);
        toast.success('Registration successful!');
        onComplete(false, data.access_token);
      } catch (error: any) {
        toast.error(error.message || 'Verification failed');
        console.error(error);
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleBack = () => {
    if (activeTab === 'register' && registerStep === 'otp') {
      setRegisterStep('phone');
    } else {
      onBack();
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-br from-[#af47ff] to-[#8b2dd1] p-6">
      <div className="mb-6 flex items-center justify-between">
        <button
          onClick={handleBack}
          className="flex items-center gap-2 text-white/90 hover:text-white"
        >
          <ArrowLeft className="h-5 w-5" />
          {activeTab === 'register' && registerStep === 'otp' ? 'Change Number' : 'Back'}
        </button>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex-1"
      >
        <h2 className="mb-2 text-white font-bold text-2xl">
          {activeTab === 'login' ? 'Welcome Back' : (registerStep === 'phone' ? 'Create Account' : 'Verification')}
        </h2>
        <p className="mb-8 text-white/80">
          {activeTab === 'login'
            ? 'Login to your account'
            : (registerStep === 'phone'
              ? 'Enter your details to continue'
              : `Enter the code sent to @${telegramUsername} on Telegram`
            )
          }
        </p>

        {activeTab === 'register' && registerStep === 'otp' ? null : (
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="mb-6">
            <TabsList className="grid w-full grid-cols-2 bg-background/20">
              <TabsTrigger value="login" className="data-[state=active]:bg-background data-[state=active]:text-[#af47ff]">
                Login
              </TabsTrigger>
              <TabsTrigger value="register" className="data-[state=active]:bg-background data-[state=active]:text-[#af47ff]">
                Register
              </TabsTrigger>
            </TabsList>

            <TabsContent value="login" className="mt-6">
              <div className="rounded-2xl bg-background p-6 shadow-xl">
                <form onSubmit={handleLoginSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="login-phone">Phone Number</Label>
                    <div className="relative">
                      <Phone className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="login-phone"
                        type="tel"
                        placeholder="+998 (90) 123-45-67"
                        value={loginPhone}
                        onChange={(e) => setLoginPhone(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="password"
                        type="password"
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                  </div>

                  <Button type="submit" className="w-full bg-[#af47ff] hover:bg-[#9935e6]" disabled={isLoading}>
                    {isLoading ? 'Logging in...' : 'Login'}
                  </Button>

                  <div className="relative my-4">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-border"></div>
                    </div>
                    <div className="relative flex justify-center text-sm">
                      <span className="bg-background px-2 text-muted-foreground">Or continue with</span>
                    </div>
                  </div>

                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    onClick={() => api.loginWithGoogle()}
                  >
                    <svg className="mr-2 h-5 w-5" viewBox="0 0 24 24">
                      <path
                        fill="#4285F4"
                        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                      />
                      <path
                        fill="#34A853"
                        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                      />
                      <path
                        fill="#FBBC05"
                        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                      />
                      <path
                        fill="#EA4335"
                        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                      />
                    </svg>
                    Sign in with Google
                  </Button>
                </form>
              </div>
            </TabsContent>

            <TabsContent value="register" className="mt-6">
              <div className="rounded-2xl bg-background p-6 shadow-xl">
                <form onSubmit={handleRegisterPhoneSubmit} className="space-y-6">
                  <div className="space-y-2">
                    <Label htmlFor="register-phone">Phone Number</Label>
                    <div className="relative">
                      <Phone className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="register-phone"
                        type="tel"
                        placeholder="+998 (90) 123-45-67"
                        value={registerPhone}
                        onChange={(e) => setRegisterPhone(e.target.value)}
                        className="pl-10 h-12 text-lg"
                        autoFocus
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="register-password">Create Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="register-password"
                        type="password"
                        placeholder="••••••••"
                        value={registerPassword}
                        onChange={(e) => setRegisterPassword(e.target.value)}
                        className="pl-10 h-12 text-lg"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="telegram-username">Telegram Username</Label>
                    <div className="relative">
                      <Send className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="telegram-username"
                        type="text"
                        placeholder="@username"
                        value={telegramUsername}
                        onChange={(e) => setTelegramUsername(e.target.value.replace(/^@+/, ''))}
                        className="pl-10 h-12 text-lg"
                      />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Open Telegram, find <strong>@UDXBot</strong>, send <code>/start</code>, then come back here.
                    </p>
                  </div>

                  <Button type="submit" className="w-full bg-[#af47ff] hover:bg-[#9935e6] h-12 text-lg font-medium" disabled={isLoading}>
                    {isLoading ? 'Sending code...' : 'Continue'}
                  </Button>

                  <div className="relative my-4">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-border"></div>
                    </div>
                    <div className="relative flex justify-center text-sm">
                      <span className="bg-background px-2 text-muted-foreground">Or continue with</span>
                    </div>
                  </div>

                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    onClick={() => api.registerWithGoogle()}
                  >
                    <svg className="mr-2 h-5 w-5" viewBox="0 0 24 24">
                      <path
                        fill="#4285F4"
                        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                      />
                      <path
                        fill="#34A853"
                        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                      />
                      <path
                        fill="#FBBC05"
                        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                      />
                      <path
                        fill="#EA4335"
                        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                      />
                    </svg>
                    Sign up with Google
                  </Button>
                </form>
              </div>
            </TabsContent>
          </Tabs>
        )}

        {/* OTP Section matches previous structure roughly but uses new handler */}
        {activeTab === 'register' && registerStep === 'otp' && (
          <div className="mt-6 rounded-2xl bg-background p-6 shadow-xl">
            <form onSubmit={handleRegisterOtpSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="code">Verification Code</Label>
                <Input
                  id="code"
                  type="text"
                  placeholder="000000"
                  value={registerCode}
                  onChange={(e) => {
                    const val = e.target.value.replace(/[^0-9]/g, '');
                    if (val.length <= 6) setRegisterCode(val);
                  }}
                  className="h-12 text-lg tracking-widest text-center font-mono text-2xl"
                  autoFocus
                  maxLength={6}
                />
                <p className="text-sm text-muted-foreground text-center">
                  Code sent to <strong>@{telegramUsername}</strong> on Telegram
                </p>
              </div>

              <Button type="submit" className="w-full bg-[#af47ff] hover:bg-[#9935e6] h-12 text-lg font-medium" disabled={registerCode.length !== 6 || isLoading}>
                {isLoading ? 'Verifying...' : 'Verify & Create Account'}
              </Button>
            </form>
          </div>
        )}

        {/* Guest Login Button */}
        <div className="mt-6 text-center">
          <button
            onClick={() => onComplete(true)}
            className="text-white/80 hover:text-white underline text-sm"
          >
            Continue as Guest
          </button>
        </div>

      </motion.div>
    </div>
  );
}
