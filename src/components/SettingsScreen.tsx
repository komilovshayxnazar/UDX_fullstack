import { ArrowLeft, User, Phone, Lock, Shield, CreditCard, Bell, MessageSquare, DollarSign, TrendingUp, Globe, Eye, Ruler, MapPin, HelpCircle, FileText, Info, LogOut, ChevronRight, RefreshCw, EyeOff } from 'lucide-react';
import { useState, useEffect } from 'react';
import { api } from '../api';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Separator } from './ui/separator';
import { Switch } from './ui/switch';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger, DialogClose } from './ui/dialog';
import { Input } from './ui/input';

interface SettingsScreenProps {
  onBack: () => void;
  onLanguageClick: () => void;
  onLogout: () => void;
  onLogin?: () => void;
  onSwitchMode?: () => void;
  currentMode?: 'buyer' | 'seller';
  user?: any;
  onTopUp?: (amount: number) => Promise<void>;
  onWithdraw?: (amount: number) => Promise<void>;
  token?: string | null;
  onUserUpdated?: (user: any) => void;
}

export function SettingsScreen({ onBack, onLanguageClick, onLogout, onLogin, onSwitchMode, currentMode = 'buyer', user, onTopUp, onWithdraw, token, onUserUpdated }: SettingsScreenProps) {
  const [phoneVisible, setPhoneVisible] = useState(false);
  const [balanceVisible, setBalanceVisible] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [topUpAmount, setTopUpAmount] = useState('');
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [topUpOpen, setTopUpOpen] = useState(false);
  const [withdrawOpen, setWithdrawOpen] = useState(false);

  const [editProfileOpen, setEditProfileOpen] = useState(false);
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);
  const [profileData, setProfileData] = useState({ name: user?.name || '', description: user?.description || '' });
  const [passwordData, setPasswordData] = useState({ current_password: '', new_password: '', confirm_password: '' });

  useEffect(() => {
    if (user) {
      setProfileData({ name: user.name || '', description: user.description || '' });
    }
  }, [user]);

  // Format phone number for display
  const formatPhoneNumber = (phone: string | undefined) => {
    if (!phone) return 'Not set';

    // Check if it's a Google OAuth user
    if (phone.startsWith('google_')) {
      return 'Google Account';
    }

    return phone;
  };

  // Mask phone number
  const maskPhoneNumber = (phone: string | undefined) => {
    if (!phone) return 'Not set';

    if (phone.startsWith('google_')) {
      return 'Google Account';
    }

    if (phone.length > 4) {
      return phone.substring(0, 4) + '•'.repeat(phone.length - 4);
    }
    return phone;
  };

  const handleTopUp = async () => {
    const amount = parseFloat(topUpAmount);
    if (isNaN(amount) || amount <= 0) {
      alert("Invalid amount");
      return;
    }
    if (onTopUp) {
      setIsProcessing(true);
      try {
        await onTopUp(amount);
        setTopUpOpen(false);
        setTopUpAmount('');
      } catch (e: any) {
        alert(e.message || "Failed to top up");
      }
      setIsProcessing(false);
    }
  };

  const handleWithdraw = async () => {
    const amount = parseFloat(withdrawAmount);
    if (isNaN(amount) || amount <= 0) {
      alert("Invalid amount");
      return;
    }
    if (onWithdraw) {
      setIsProcessing(true);
      try {
        await onWithdraw(amount);
        setWithdrawOpen(false);
        setWithdrawAmount('');
      } catch (e: any) {
        alert(e.message || "Failed to withdraw");
      }
      setIsProcessing(false);
    }
  };

  const handleUpdateProfile = async () => {
    if (!token) return;
    setIsProcessing(true);
    try {
      const updatedUser = await api.updateProfile(profileData, token);
      if (onUserUpdated) onUserUpdated(updatedUser);
      setEditProfileOpen(false);
      toast.success('Profile updated successfully');
    } catch (e: any) {
      toast.error(e.message || 'Failed to update profile');
    }
    setIsProcessing(false);
  };

  const handleChangePassword = async () => {
    if (!token) return;
    if (passwordData.new_password !== passwordData.confirm_password) {
      toast.error('Passwords do not match');
      return;
    }
    setIsProcessing(true);
    try {
      await api.changePassword({ current_password: passwordData.current_password, new_password: passwordData.new_password }, token);
      setChangePasswordOpen(false);
      setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
      toast.success('Password changed successfully');
    } catch (e: any) {
      toast.error(e.message || 'Failed to change password');
    }
    setIsProcessing(false);
  };

  const handleToggle2FA = async (enabled: boolean) => {
    if (!token) return;
    try {
      const updatedUser = await api.update2FA(enabled, token);
      if (onUserUpdated) onUserUpdated(updatedUser);
      toast.success(enabled ? 'Two-Factor Authentication enabled' : 'Two-Factor Authentication disabled');
    } catch (e: any) {
      toast.error(e.message || 'Failed to update 2FA settings');
    }
  };

  const displayPhone = phoneVisible ? formatPhoneNumber(user?.phone) : maskPhoneNumber(user?.phone);
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white px-4 py-4 shadow-sm">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="rounded-full p-2 hover:bg-gray-100">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <h2>Settings</h2>
        </div>
      </div>

      <div className="px-4 py-6">
        {/* User Profile Card */}
        <Card className="mb-6 p-4">
          <div className="flex items-center gap-4">
            <Avatar className="h-16 w-16">
              <AvatarImage src={user?.avatar || "https://images.unsplash.com/photo-1633332755192-727a05c4013d?w=200"} />
              <AvatarFallback>{user?.name?.split(' ').map((n: string) => n[0]).join('').toUpperCase() || 'U'}</AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <h3>{user?.name || 'Guest User'}</h3>
              <p className="text-gray-600">{user?.role ? user.role.charAt(0).toUpperCase() + user.role.slice(1) : 'Guest'}</p>
              {user && user.name !== 'Guest User' && (
                <div className="flex items-center gap-2 mt-1">
                  <p className="text-sm font-semibold text-green-600">
                    Balance: {balanceVisible ? `$${user?.balance?.toFixed(2) || '0.00'}` : '******'}
                  </p>
                  <button onClick={() => setBalanceVisible(!balanceVisible)} className="p-1 hover:bg-gray-100 rounded-full cursor-pointer">
                    {balanceVisible ? <EyeOff className="h-4 w-4 text-gray-500" /> : <Eye className="h-4 w-4 text-gray-500" />}
                  </button>
                </div>
              )}
            </div>

            {user && user.name !== 'Guest User' ? (
              <div className="flex flex-col gap-2">
                <Dialog open={topUpOpen} onOpenChange={setTopUpOpen}>
                  <DialogTrigger asChild>
                    <Button size="sm" className="bg-green-600 hover:bg-green-700 text-white h-7 text-xs">
                      Top Up
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Top Up Balance</DialogTitle>
                      <DialogDescription>Enter the amount you would like to deposit into your account.</DialogDescription>
                    </DialogHeader>
                    <div className="py-4">
                      <Input
                        type="number"
                        placeholder="Amount ($)"
                        value={topUpAmount}
                        onChange={(e) => setTopUpAmount(e.target.value)}
                        min="0.01"
                        step="0.01"
                      />
                    </div>
                    <DialogFooter>
                      <Button variant="outline" onClick={() => setTopUpOpen(false)}>Cancel</Button>
                      <Button onClick={handleTopUp} disabled={isProcessing || !topUpAmount} className="bg-green-600 hover:bg-green-700 text-white">
                        {isProcessing ? 'Processing...' : 'Confirm'}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>

                <Dialog open={withdrawOpen} onOpenChange={setWithdrawOpen}>
                  <DialogTrigger asChild>
                    <Button variant="outline" size="sm" className="h-7 text-xs">
                      Withdraw
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Withdraw Funds</DialogTitle>
                      <DialogDescription>Enter the amount you would like to withdraw from your available balance.</DialogDescription>
                    </DialogHeader>
                    <div className="py-4">
                      <Input
                        type="number"
                        placeholder="Amount ($)"
                        value={withdrawAmount}
                        onChange={(e) => setWithdrawAmount(e.target.value)}
                        min="0.01"
                        step="0.01"
                        max={user?.balance || 0}
                      />
                    </div>
                    <DialogFooter>
                      <Button variant="outline" onClick={() => setWithdrawOpen(false)}>Cancel</Button>
                      <Button onClick={handleWithdraw} disabled={isProcessing || !withdrawAmount} className="bg-green-600 hover:bg-green-700 text-white">
                        {isProcessing ? 'Processing...' : 'Confirm'}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                <Button onClick={onLogin} size="sm" className="bg-green-600 hover:bg-green-700 text-white h-7 text-xs">
                  Log In
                </Button>
                <Button onClick={onLogin} variant="outline" size="sm" className="h-7 text-xs">
                  Sign Up
                </Button>
              </div>
            )}
          </div>
        </Card>

        {/* Account and Security */}
        <div className="mb-6">
          <h3 className="mb-3 px-2 text-gray-600">Account & Security</h3>
          <Card className="overflow-hidden">
            <Dialog open={editProfileOpen} onOpenChange={setEditProfileOpen}>
              <DialogTrigger asChild>
                <div>
                  <SettingsItem icon={<User />} label="Edit Profile" sublabel="Name, company, contacts" onClick={() => setEditProfileOpen(true)} />
                </div>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Edit Profile</DialogTitle>
                </DialogHeader>
                <div className="flex flex-col gap-4 py-4">
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium">Name</label>
                    <Input value={profileData.name} onChange={(e) => setProfileData({ ...profileData, name: e.target.value })} placeholder="Your Name" />
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium">Description / Company</label>
                    <Input value={profileData.description} onChange={(e) => setProfileData({ ...profileData, description: e.target.value })} placeholder="Description" />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setEditProfileOpen(false)}>Cancel</Button>
                  <Button onClick={handleUpdateProfile} disabled={isProcessing} className="bg-green-600 hover:bg-green-700 text-white">Save Changes</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
            <Separator />
            <div className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50" onClick={() => { }}>
              <div className="flex items-center gap-3">
                <Phone className="h-5 w-5 text-gray-600" />
                <div>
                  <div className="font-medium">Phone Number</div>
                  <div className="text-sm text-gray-600">{displayPhone}</div>
                </div>
              </div>
              {user?.phone && !user.phone.startsWith('google_') && (
                <button
                  onClick={(e) => { e.stopPropagation(); setPhoneVisible(!phoneVisible); }}
                  className="rounded-full p-2 hover:bg-gray-200 transition-colors"
                >
                  {phoneVisible ? (
                    <EyeOff className="h-5 w-5 text-gray-600" />
                  ) : (
                    <Eye className="h-5 w-5 text-gray-600" />
                  )}
                </button>
              )}
            </div>
            <Separator />
            <Dialog open={changePasswordOpen} onOpenChange={setChangePasswordOpen}>
              <DialogTrigger asChild>
                <div>
                  <SettingsItem icon={<Lock />} label="Change Password" onClick={() => setChangePasswordOpen(true)} />
                </div>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Change Password</DialogTitle>
                </DialogHeader>
                <div className="flex flex-col gap-4 py-4">
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium">Current Password</label>
                    <Input type="password" value={passwordData.current_password} onChange={(e) => setPasswordData({ ...passwordData, current_password: e.target.value })} />
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium">New Password</label>
                    <Input type="password" value={passwordData.new_password} onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })} />
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium">Confirm New Password</label>
                    <Input type="password" value={passwordData.confirm_password} onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })} />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setChangePasswordOpen(false)}>Cancel</Button>
                  <Button onClick={handleChangePassword} disabled={isProcessing} className="bg-green-600 hover:bg-green-700 text-white">Update Password</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
            <Separator />
            <SettingsItem icon={<Shield />} label="Two-Factor Authentication" hasSwitch defaultChecked={user?.is_2fa_enabled || false} onCheckedChange={handleToggle2FA} />
            <Separator />
            <SettingsItem icon={<CreditCard />} label="Payment Details" sublabel="Manage cards and methods" onClick={() => { }} />
          </Card>
        </div>

        {/* Notifications */}
        <div className="mb-6">
          <h3 className="mb-3 px-2 text-gray-600">Notifications</h3>
          <Card className="overflow-hidden">
            <SettingsItem icon={<Bell />} label="Push Notifications" hasSwitch defaultChecked />
            <Separator />
            <SettingsItem icon={<MessageSquare />} label="Messages from Sellers" hasSwitch defaultChecked />
            <Separator />
            <SettingsItem icon={<DollarSign />} label="Price Changes & Orders" hasSwitch defaultChecked />
            <Separator />
            <SettingsItem icon={<TrendingUp />} label="Market News & Analytics" hasSwitch />
            <Separator />
            <SettingsItem icon={<Info />} label="System Notifications" hasSwitch defaultChecked />
          </Card>
        </div>

        {/* Privacy */}
        <div className="mb-6">
          <h3 className="mb-3 px-2 text-gray-600">Privacy</h3>
          <Card className="overflow-hidden">
            <SettingsItem icon={<Eye />} label="Profile Visibility" sublabel="All users" />
          </Card>
        </div>

        {/* Preferences */}
        <div className="mb-6">
          <h3 className="mb-3 px-2 text-gray-600">Preferences</h3>
          <Card className="overflow-hidden">
            <SettingsItem icon={<Globe />} label="Language" sublabel="English" onClick={onLanguageClick} />
            <Separator />
            <SettingsItem icon={<Ruler />} label="Units of Measurement" sublabel="kg, tons, liters" onClick={() => { }} />
            <Separator />
            <SettingsItem icon={<DollarSign />} label="Currency" sublabel="USD ($)" onClick={() => { }} />
            <Separator />
            <SettingsItem icon={<MapPin />} label="Product Search Region" sublabel="Current location" onClick={() => { }} />
          </Card>
        </div>

        {/* About */}
        <div className="mb-6">
          <h3 className="mb-3 px-2 text-gray-600">About the App</h3>
          <Card className="overflow-hidden">
            <SettingsItem icon={<HelpCircle />} label="Help & Support" sublabel="Chat, FAQ" onClick={() => { }} />
            <Separator />
            <SettingsItem icon={<FileText />} label="Terms of Use" onClick={() => { }} />
            <Separator />
            <SettingsItem icon={<FileText />} label="Privacy Policy" onClick={() => { }} />
            <Separator />
            <div className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50" onClick={() => { }}>
              <div className="flex items-center gap-3">
                <Info className="h-5 w-5 text-gray-500" />
                <span className="text-gray-600">App Version</span>
              </div>
              <span className="text-gray-500">v1.0.0</span>
            </div>
          </Card>
        </div>

        {/* Logout Button */}
        <Button
          onClick={onLogout}
          variant="destructive"
          className="w-full"
          size="lg"
        >
          <LogOut className="mr-2 h-5 w-5" />
          Log Out
        </Button>
      </div>
    </div>
  );
}

interface SettingsItemProps {
  icon: React.ReactNode;
  label: string;
  sublabel?: string;
  hasSwitch?: boolean;
  defaultChecked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  onClick?: () => void;
}

function SettingsItem({ icon, label, sublabel, hasSwitch, defaultChecked, onCheckedChange, onClick }: SettingsItemProps) {
  const content = (
    <>
      <div className="text-gray-500">{icon}</div>
      <div className="flex-1">
        <div>{label}</div>
        {sublabel && <div className="text-gray-500">{sublabel}</div>}
      </div>
      {hasSwitch ? (
        <Switch defaultChecked={defaultChecked} onCheckedChange={onCheckedChange} />
      ) : onClick ? (
        <ChevronRight className="h-5 w-5 text-gray-400" />
      ) : null}
    </>
  );

  if (hasSwitch) {
    return (
      <label className="flex w-full cursor-pointer items-center gap-3 p-4 text-left hover:bg-gray-50">
        {content}
      </label>
    );
  }

  if (onClick) {
    return (
      <button
        onClick={onClick}
        className="flex w-full items-center gap-3 p-4 text-left hover:bg-gray-50"
      >
        {content}
      </button>
    );
  }

  return (
    <div className="flex w-full items-center gap-3 p-4 text-left">
      {content}
    </div>
  );
}
