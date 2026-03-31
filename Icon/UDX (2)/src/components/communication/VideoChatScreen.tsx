import { useState } from 'react';
import { motion } from 'motion/react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { 
  Phone, 
  Video, 
  VideoOff, 
  Mic, 
  MicOff, 
  Settings, 
  MessageCircle, 
  Languages,
  Heart,
  Monitor,
  Users,
  MoreVertical
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner@2.0.3';

interface VideoChatScreenProps {
  farmerName: string;
  farmerId?: string;
  onEndCall: () => void;
  onAddToFavorites?: (farmerId: string) => void;
  isFavorite?: boolean;
}

export function VideoChatScreen({ 
  farmerName, 
  farmerId = '1',
  onEndCall,
  onAddToFavorites,
  isFavorite = false
}: VideoChatScreenProps) {
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);
  const [myLanguage, setMyLanguage] = useState('en');
  const [partnerLanguage, setPartnerLanguage] = useState('tr');
  const [chatMessage, setChatMessage] = useState('');
  const [translationMode, setTranslationMode] = useState<'chat' | 'voice'>('voice');
  const [isLiked, setIsLiked] = useState(isFavorite);
  
  // Simulated real-time translation
  const [liveTranscript] = useState({
    original: 'Elmalar taze mi?',
    translated: 'Are the apples fresh?',
  });

  const handleSendMessage = () => {
    if (chatMessage.trim()) {
      // Message would be automatically translated
      setChatMessage('');
    }
  };

  const handleToggleFavorite = () => {
    setIsLiked(!isLiked);
    if (!isLiked) {
      onAddToFavorites?.(farmerId);
      toast.success(`${farmerName} added to favorites`);
    } else {
      toast.success(`${farmerName} removed from favorites`);
    }
  };

  return (
    <div className="flex h-screen flex-col bg-black">
      {/* Top Panel with Google Meet Style Controls */}
      <div className="flex items-center justify-between bg-gradient-to-r from-[#af47ff] to-[#8b2dd1] px-4 py-3 text-white">
        <div className="flex items-center gap-3">
          <div>
            <h3 className="text-white">{farmerName}</h3>
            <div className="flex items-center gap-2">
              <Badge className="bg-green-500">Online</Badge>
            </div>
          </div>
        </div>
        
        <div className="flex gap-2">
          {/* Mic Control */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => {
              setIsMuted(!isMuted);
              toast.info(isMuted ? 'Microphone on' : 'Microphone off');
            }}
            className={`text-white hover:bg-white/20 ${isMuted ? 'bg-red-500/50' : ''}`}
          >
            {isMuted ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
          </Button>

          {/* Video Control */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => {
              setIsVideoOff(!isVideoOff);
              toast.info(isVideoOff ? 'Camera on' : 'Camera off');
            }}
            className={`text-white hover:bg-white/20 ${isVideoOff ? 'bg-red-500/50' : ''}`}
          >
            {isVideoOff ? <VideoOff className="h-5 w-5" /> : <Video className="h-5 w-5" />}
          </Button>

          {/* Screen Share */}
          <Button
            variant="ghost"
            size="icon"
            className="text-white hover:bg-white/20"
            onClick={() => toast.info('Screen sharing feature')}
          >
            <Monitor className="h-5 w-5" />
          </Button>

          {/* More Options */}
          <Button
            variant="ghost"
            size="icon"
            className="text-white hover:bg-white/20"
          >
            <MoreVertical className="h-5 w-5" />
          </Button>

          {/* Heart/Favorite Button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={handleToggleFavorite}
            className="text-white hover:bg-white/20"
          >
            <Heart 
              className={`h-5 w-5 ${isLiked ? 'fill-red-500 text-red-500' : ''}`}
            />
          </Button>

          {/* End Call */}
          <Button
            variant="ghost"
            size="icon"
            onClick={onEndCall}
            className="bg-red-500 text-white hover:bg-red-600"
          >
            <Phone className="h-5 w-5" />
          </Button>
        </div>
      </div>

      {/* Video Area */}
      <div className="relative flex-1 bg-gray-900">
        {/* Main video (partner) */}
        <div className="h-full w-full bg-gray-800 flex items-center justify-center">
          <div className="text-center text-white">
            <Video className="mx-auto mb-2 h-12 w-12" />
            <p>{farmerName}'s Video</p>
          </div>
        </div>

        {/* Picture-in-picture (self) */}
        <motion.div
          drag
          dragConstraints={{ top: 0, bottom: 400, left: 0, right: 250 }}
          className="absolute right-4 top-4 h-32 w-24 cursor-move overflow-hidden rounded-xl border-2 border-white bg-gray-700"
        >
          <div className="flex h-full items-center justify-center text-white">
            <Video className="h-6 w-6" />
          </div>
        </motion.div>

        {/* Participant Info Overlay */}
        <div className="absolute bottom-4 left-4 rounded-lg bg-black/50 px-3 py-2 text-white">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            <span>2 participants</span>
          </div>
        </div>
      </div>

      {/* Translation Panel */}
      <div className="bg-white">
        <Tabs value={translationMode} onValueChange={(v) => setTranslationMode(v as 'chat' | 'voice')}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="chat">
              <MessageCircle className="mr-2 h-4 w-4" />
              Text Chat
            </TabsTrigger>
            <TabsTrigger value="voice">
              <Languages className="mr-2 h-4 w-4" />
              Voice Translation
            </TabsTrigger>
          </TabsList>

          <TabsContent value="chat" className="p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-gray-600">Messages auto-translate</span>
              <Dialog>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Settings className="mr-2 h-4 w-4" />
                    Languages
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Translation Settings</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <label className="mb-2 block">My Language</label>
                      <Select value={myLanguage} onValueChange={setMyLanguage}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="en">🇺🇸 English</SelectItem>
                          <SelectItem value="ru">🇷🇺 Russian</SelectItem>
                          <SelectItem value="uz">🇺🇿 Uzbek</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <label className="mb-2 block">Partner's Language</label>
                      <Select value={partnerLanguage} onValueChange={setPartnerLanguage}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="tr">🇹🇷 Turkish</SelectItem>
                          <SelectItem value="en">🇺🇸 English</SelectItem>
                          <SelectItem value="ar">🇦🇪 Arabic</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
            <div className="flex gap-2">
              <Input
                placeholder="Type your message..."
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              />
              <Button onClick={handleSendMessage} className="bg-[#af47ff] hover:bg-[#9935e6]">
                Send
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="voice" className="p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-gray-600">Live voice translation</span>
              <Dialog>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Settings className="mr-2 h-4 w-4" />
                    {myLanguage.toUpperCase()} → {partnerLanguage.toUpperCase()}
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Translation Settings</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <label className="mb-2 block">I speak</label>
                      <Select value={myLanguage} onValueChange={setMyLanguage}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="en">🇺🇸 English</SelectItem>
                          <SelectItem value="ru">🇷🇺 Russian</SelectItem>
                          <SelectItem value="uz">🇺🇿 Uzbek</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <label className="mb-2 block">Partner speaks</label>
                      <Select value={partnerLanguage} onValueChange={setPartnerLanguage}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="tr">🇹🇷 Turkish</SelectItem>
                          <SelectItem value="en">🇺🇸 English</SelectItem>
                          <SelectItem value="ar">🇦🇪 Arabic</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            {/* Live Subtitles */}
            <div className="space-y-3 rounded-xl bg-gray-50 p-4">
              <div>
                <Badge className="mb-2 bg-blue-500">Partner speaking (Turkish)</Badge>
                <p className="mb-1">{liveTranscript.original}</p>
                <p className="text-[#af47ff]">↓ {liveTranscript.translated}</p>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
