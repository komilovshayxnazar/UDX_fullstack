import { useState } from 'react';
import { motion } from 'motion/react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { ArrowLeft, User, MapPin, Briefcase, Store } from 'lucide-react';
import { useTranslation } from '../context/TranslationContext';

interface UnifiedProfileScreenProps {
  onComplete: () => void;
  onBack: () => void;
}

export function UnifiedProfileScreen({ onComplete, onBack }: UnifiedProfileScreenProps) {
  const { t } = useTranslation();
  const [step, setStep] = useState<'personal' | 'buyer' | 'seller'>('personal');
  
  // Personal info
  const [name, setName] = useState('');
  const [location, setLocation] = useState('');
  
  // Buyer info
  const [buyerInterests, setBuyerInterests] = useState<string[]>([]);
  const [deliveryPreference, setDeliveryPreference] = useState('');
  
  // Seller info
  const [businessName, setBusinessName] = useState('');
  const [businessType, setBusinessType] = useState('');
  const [sellerDescription, setSellerDescription] = useState('');

  const categories = [
    'Fruits', 'Vegetables', 'Grains', 'Dairy', 'Meat', 'Honey', 
    'Nuts', 'Herbs', 'Flowers', 'Seeds', 'Greens'
  ];

  const handleNext = () => {
    if (step === 'personal') {
      setStep('buyer');
    } else if (step === 'buyer') {
      setStep('seller');
    } else {
      onComplete();
    }
  };

  const handleBack = () => {
    if (step === 'seller') {
      setStep('buyer');
    } else if (step === 'buyer') {
      setStep('personal');
    } else {
      onBack();
    }
  };

  const toggleInterest = (category: string) => {
    setBuyerInterests(prev => 
      prev.includes(category) 
        ? prev.filter(c => c !== category)
        : [...prev, category]
    );
  };

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-br from-[#af47ff] via-[#9935e6] to-[#7c24cc]">
      {/* Header */}
      <div className="flex items-center justify-between bg-white/10 p-4 backdrop-blur-sm">
        <button onClick={handleBack} className="rounded-full p-2 hover:bg-white/10">
          <ArrowLeft className="h-6 w-6 text-white" />
        </button>
        <h2 className="text-white">
          {step === 'personal' && 'Personal Information'}
          {step === 'buyer' && 'Buyer Profile'}
          {step === 'seller' && 'Seller Profile'}
        </h2>
        <div className="w-10" />
      </div>

      {/* Progress Indicator */}
      <div className="px-6 pt-4">
        <div className="flex gap-2">
          <div className={`h-1 flex-1 rounded-full ${step === 'personal' ? 'bg-white' : 'bg-white/30'}`} />
          <div className={`h-1 flex-1 rounded-full ${step === 'buyer' ? 'bg-white' : 'bg-white/30'}`} />
          <div className={`h-1 flex-1 rounded-full ${step === 'seller' ? 'bg-white' : 'bg-white/30'}`} />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          className="mx-auto max-w-md"
        >
          {/* Personal Information */}
          {step === 'personal' && (
            <div className="space-y-6 rounded-2xl bg-white p-6 shadow-xl">
              <div className="text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-[#af47ff] to-[#9935e6]">
                  <User className="h-8 w-8 text-white" />
                </div>
                <h3 className="mb-2">Tell us about yourself</h3>
                <p className="text-gray-600">This information will be used for both buying and selling</p>
              </div>

              <div className="space-y-4">
                <div>
                  <Label htmlFor="name">Full Name *</Label>
                  <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Enter your full name"
                    className="mt-1"
                  />
                </div>

                <div>
                  <Label htmlFor="location">Location *</Label>
                  <div className="relative mt-1">
                    <MapPin className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <Input
                      id="location"
                      value={location}
                      onChange={(e) => setLocation(e.target.value)}
                      placeholder="City, Country"
                      className="pl-10"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Buyer Profile */}
          {step === 'buyer' && (
            <div className="space-y-6 rounded-2xl bg-white p-6 shadow-xl">
              <div className="text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-[#af47ff] to-[#9935e6]">
                  <Briefcase className="h-8 w-8 text-white" />
                </div>
                <h3 className="mb-2">Buyer Preferences</h3>
                <p className="text-gray-600">Help us personalize your buying experience</p>
              </div>

              <div className="space-y-4">
                <div>
                  <Label>What are you interested in buying? *</Label>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {categories.map((category) => (
                      <button
                        key={category}
                        onClick={() => toggleInterest(category)}
                        className={`rounded-full px-4 py-2 transition-all ${
                          buyerInterests.includes(category)
                            ? 'bg-[#af47ff] text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {category}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <Label htmlFor="delivery">Preferred Delivery Method</Label>
                  <Select value={deliveryPreference} onValueChange={setDeliveryPreference}>
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder="Select delivery preference" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="courier">Courier Delivery</SelectItem>
                      <SelectItem value="pickup">Self Pickup</SelectItem>
                      <SelectItem value="both">Both</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          )}

          {/* Seller Profile */}
          {step === 'seller' && (
            <div className="space-y-6 rounded-2xl bg-white p-6 shadow-xl">
              <div className="text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-[#af47ff] to-[#9935e6]">
                  <Store className="h-8 w-8 text-white" />
                </div>
                <h3 className="mb-2">Seller Profile</h3>
                <p className="text-gray-600">Set up your selling business</p>
              </div>

              <div className="space-y-4">
                <div>
                  <Label htmlFor="businessName">Business/Farm Name *</Label>
                  <Input
                    id="businessName"
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                    placeholder="Enter your business name"
                    className="mt-1"
                  />
                </div>

                <div>
                  <Label htmlFor="businessType">Business Type</Label>
                  <Select value={businessType} onValueChange={setBusinessType}>
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder="Select business type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="farm">Farm</SelectItem>
                      <SelectItem value="cooperative">Cooperative</SelectItem>
                      <SelectItem value="wholesaler">Wholesaler</SelectItem>
                      <SelectItem value="retailer">Retailer</SelectItem>
                      <SelectItem value="producer">Producer</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="description">Business Description</Label>
                  <Textarea
                    id="description"
                    value={sellerDescription}
                    onChange={(e) => setSellerDescription(e.target.value)}
                    placeholder="Tell buyers about your business..."
                    className="mt-1 min-h-[100px]"
                  />
                </div>
              </div>
            </div>
          )}
        </motion.div>
      </div>

      {/* Footer */}
      <div className="border-t border-white/10 bg-white/10 p-4 backdrop-blur-sm">
        <Button
          onClick={handleNext}
          disabled={
            (step === 'personal' && (!name || !location)) ||
            (step === 'buyer' && buyerInterests.length === 0) ||
            (step === 'seller' && !businessName)
          }
          className="w-full bg-white text-[#af47ff] hover:bg-white/90"
        >
          {step === 'seller' ? 'Complete Profile' : 'Continue'}
        </Button>
      </div>
    </div>
  );
}