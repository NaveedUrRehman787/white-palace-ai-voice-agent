import { useState, useCallback } from 'react';
import { useLiveKitRoom, RoomAudioRenderer, ControlBar } from '@livekit/components-react';
import '@livekit/components-styles';
import { Mic, MicOff, Phone, Loader2, Volume2 } from 'lucide-react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';

export default function VoiceAgent() {
    const [token, setToken] = useState('');
    const [url, setUrl] = useState('');
    const [isConnected, setIsConnected] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const startCall = async () => {
        setLoading(true);
        setError('');

        try {
            // 1. Create Room & Get Token
            // For demo, we use a fake phone number or user ID
            const customerPhone = "+15550000000";

            const res = await axios.post('/api/voice/create-room', { customerPhone });
            const { customerToken, livekitUrl } = res.data.data;

            setToken(customerToken);
            setUrl(livekitUrl);
            setIsConnected(true);

        } catch (err) {
            console.error(err);
            setError("Unable to start call. Please check if the backend is running.");
        } finally {
            setLoading(false);
        }
    };

    const handleDisconnect = () => {
        setIsConnected(false);
        setToken('');
    };

    return (
        <div className="voice-page container page-padding">
            <div className="page-header">
                <h1>AI Voice Assistant</h1>
                <p>Talk to our intelligent agent to place orders or make reservations naturally.</p>
            </div>

            <div className="voice-container">
                {!isConnected ? (
                    <motion.div
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="call-starter"
                    >
                        <div className="pulse-circle">
                            <Phone size={48} className="phone-icon" />
                        </div>

                        {error && <p className="error-text">{error}</p>}

                        <button
                            onClick={startCall}
                            disabled={loading}
                            className="btn btn-primary btn-lg"
                        >
                            {loading ? (
                                <> <Loader2 className="animate-spin" /> Connecting... </>
                            ) : (
                                <> Start Voice Call </>
                            )}
                        </button>
                        <p className="hint">Microphone access required</p>
                    </motion.div>
                ) : (
                    <LiveKitRoomWrapper
                        token={token}
                        serverUrl={url}
                        onDisconnect={handleDisconnect}
                    />
                )}
            </div>
        </div>
    );
}

function LiveKitRoomWrapper({ token, serverUrl, onDisconnect }) {
    return (
        <div className="livekit-wrapper">
            {/* LiveKit Room Component */}
            <div className="active-call-ui">
                <motion.div
                    className="visualizer"
                    animate={{ scale: [1, 1.1, 1] }}
                    transition={{ repeat: Infinity, duration: 2 }}
                >
                    <div className="visualizer-core">
                        <Volume2 size={64} />
                    </div>
                </motion.div>
                <h2>Connected to White Palace</h2>
                <p>Listening...</p>
            </div>

            {/* Hidden Actual Logic */}
            <div style={{ display: 'none' }}>
                {/* Must be imported dynamically or handled by separate component if using pure JS SDK, 
                but here we use the React Components package which simplifies it */}
            </div>

            {/* We use specific Logic Component to bridge hooks if needed, otherwise use bare room */}
            <ActiveRoom token={token} url={serverUrl} onDisconnect={onDisconnect} />
        </div>
    )
}

function ActiveRoom({ token, url, onDisconnect }) {
    // This component is wrapped in LiveKitRoom by the parent if we used it directly, 
    // but here we manually implement a simple version or use the provided context.
    // For simplicity with the installed package:

    return (
        <div className="room-controls">
            {/* The actual room connection is handled by this Higher Order Component from the lib usually. 
                Let's use the standard way: */}
            <LiveKitComponent token={token} url={url} onDisconnect={onDisconnect} />
        </div>
    )
}

import { LiveKitRoom } from '@livekit/components-react';

function LiveKitComponent({ token, url, onDisconnect }) {
    return (
        <LiveKitRoom
            video={false}
            audio={true}
            token={token}
            serverUrl={url}
            connect={true}
            onDisconnected={onDisconnect}
            data-lk-theme="default"
            style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}
        >
            <RoomAudioRenderer />

            {/* Custom Controls */}
            <div className="custom-control-bar">
                <ControlBar
                    variation="minimal"
                    controls={{ microphone: true, camera: false, screenShare: false, chat: false }}
                />
                <button className="btn btn-danger" onClick={onDisconnect}>
                    End Call
                </button>
            </div>
        </LiveKitRoom>
    );
}
