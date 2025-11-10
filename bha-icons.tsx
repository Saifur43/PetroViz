import React from 'react';

const BHAIcons = () => {
  const icons = [
    {
      id: 'bit',
      name: 'Drill Bit',
      svg: (
        <svg viewBox="0 0 100 100" className="w-20 h-20">
          <defs>
            <linearGradient id="bitGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#4a5568" />
              <stop offset="100%" stopColor="#2d3748" />
            </linearGradient>
          </defs>
          <rect x="42" y="0" width="16" height="35" fill="url(#bitGrad)" />
          <path d="M 35 35 L 65 35 L 70 50 L 65 75 L 35 75 L 30 50 Z" fill="url(#bitGrad)" stroke="#1a202c" strokeWidth="1"/>
          <polygon points="35,75 30,82 35,90" fill="#718096"/>
          <polygon points="50,75 45,85 50,100" fill="#718096"/>
          <polygon points="65,75 70,82 65,90" fill="#718096"/>
          <polygon points="42,75 38,85 42,95" fill="#718096"/>
          <polygon points="58,75 62,85 58,95" fill="#718096"/>
        </svg>
      )
    },
    {
      id: 'stabilizer',
      name: 'Stabilizer',
      svg: (
        <svg viewBox="0 0 100 100" className="w-20 h-20">
          <defs>
            <linearGradient id="stabGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#2c5282" />
              <stop offset="100%" stopColor="#1a365d" />
            </linearGradient>
          </defs>
          <rect x="43" y="0" width="14" height="20" fill="url(#stabGrad)"/>
          <rect x="35" y="20" width="30" height="60" fill="url(#stabGrad)" stroke="#1a202c" strokeWidth="1"/>
          <line x1="35" y1="35" x2="65" y2="35" stroke="#4299e1" strokeWidth="2"/>
          <line x1="35" y1="50" x2="65" y2="50" stroke="#4299e1" strokeWidth="2"/>
          <line x1="35" y1="65" x2="65" y2="65" stroke="#4299e1" strokeWidth="2"/>
          <rect x="43" y="80" width="14" height="20" fill="url(#stabGrad)"/>
        </svg>
      )
    },
    {
      id: 'drill_collar',
      name: 'Drill Collar',
      svg: (
        <svg viewBox="0 0 100 100" className="w-20 h-20">
          <defs>
            <linearGradient id="collarGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#744210" />
              <stop offset="100%" stopColor="#5a2f0a" />
            </linearGradient>
          </defs>
          <rect x="38" y="0" width="24" height="100" fill="url(#collarGrad)" stroke="#2d3748" strokeWidth="1"/>
          <rect x="35" y="0" width="30" height="8" fill="#975a16"/>
          <rect x="35" y="92" width="30" height="8" fill="#975a16"/>
          <line x1="38" y1="25" x2="62" y2="25" stroke="#b7791f" strokeWidth="1"/>
          <line x1="38" y1="50" x2="62" y2="50" stroke="#b7791f" strokeWidth="1"/>
          <line x1="38" y1="75" x2="62" y2="75" stroke="#b7791f" strokeWidth="1"/>
        </svg>
      )
    },
    {
      id: 'heavy_weight',
      name: 'Heavy Weight Drill Pipe',
      svg: (
        <svg viewBox="0 0 100 100" className="w-20 h-20">
          <defs>
            <linearGradient id="hwdpGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#9c4221" />
              <stop offset="100%" stopColor="#742a13" />
            </linearGradient>
          </defs>
          <rect x="38" y="0" width="24" height="15" fill="#b7791f"/>
          <rect x="40" y="15" width="20" height="35" fill="url(#hwdpGrad)" stroke="#2d3748" strokeWidth="1"/>
          <path d="M 40 50 L 42 70 L 42 100 L 58 100 L 58 70 L 60 50 Z" fill="url(#hwdpGrad)" stroke="#2d3748" strokeWidth="1"/>
        </svg>
      )
    },
    {
      id: 'drill_pipe',
      name: 'Drill Pipe',
      svg: (
        <svg viewBox="0 0 100 100" className="w-20 h-20">
          <defs>
            <linearGradient id="pipeGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#cbd5e0" />
              <stop offset="100%" stopColor="#a0aec0" />
            </linearGradient>
          </defs>
          <rect x="40" y="0" width="20" height="12" fill="#718096"/>
          <rect x="44" y="0" width="12" height="100" fill="url(#pipeGrad)" stroke="#4a5568" strokeWidth="1"/>
          <rect x="40" y="88" width="20" height="12" fill="#718096"/>
        </svg>
      )
    },
    {
      id: 'jar',
      name: 'Jar',
      svg: (
        <svg viewBox="0 0 100 100" className="w-20 h-20">
          <defs>
            <linearGradient id="jarGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#38a169" />
              <stop offset="100%" stopColor="#276749" />
            </linearGradient>
          </defs>
          <rect x="42" y="0" width="16" height="25" fill="url(#jarGrad)"/>
          <rect x="36" y="25" width="28" height="45" fill="url(#jarGrad)" stroke="#22543d" strokeWidth="2"/>
          <rect x="38" y="35" width="24" height="5" fill="#48bb78"/>
          <rect x="38" y="55" width="24" height="5" fill="#48bb78"/>
          <rect x="42" y="70" width="16" height="30" fill="url(#jarGrad)"/>
        </svg>
      )
    },
    {
      id: 'mwd',
      name: 'MWD Tool',
      svg: (
        <svg viewBox="0 0 100 100" className="w-20 h-20">
          <defs>
            <linearGradient id="mwdGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#667eea" />
              <stop offset="100%" stopColor="#4c51bf" />
            </linearGradient>
          </defs>
          <rect x="43" y="0" width="14" height="15" fill="#5a67d8"/>
          <rect x="38" y="15" width="24" height="70" fill="url(#mwdGrad)" stroke="#434190" strokeWidth="1"/>
          <circle cx="50" cy="35" r="6" fill="#edf2f7" opacity="0.3"/>
          <circle cx="50" cy="50" r="6" fill="#edf2f7" opacity="0.3"/>
          <circle cx="50" cy="65" r="6" fill="#edf2f7" opacity="0.3"/>
          <rect x="40" y="33" width="4" height="4" fill="#9ae6b4"/>
          <rect x="56" y="33" width="4" height="4" fill="#9ae6b4"/>
          <rect x="43" y="85" width="14" height="15" fill="#5a67d8"/>
        </svg>
      )
    },
    {
      id: 'motor',
      name: 'Downhole Motor',
      svg: (
        <svg viewBox="0 0 100 100" className="w-20 h-20">
          <defs>
            <linearGradient id="motorGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#e53e3e" />
              <stop offset="100%" stopColor="#c53030" />
            </linearGradient>
          </defs>
          <rect x="43" y="0" width="14" height="12" fill="#9b2c2c"/>
          <rect x="37" y="12" width="26" height="60" fill="url(#motorGrad)" stroke="#742a2a" strokeWidth="1"/>
          <ellipse cx="50" cy="25" rx="10" ry="3" fill="#fc8181" opacity="0.5"/>
          <ellipse cx="50" cy="42" rx="10" ry="3" fill="#fc8181" opacity="0.5"/>
          <ellipse cx="50" cy="59" rx="10" ry="3" fill="#fc8181" opacity="0.5"/>
          <path d="M 42 72 L 40 82 L 38 100 L 62 100 L 60 82 L 58 72 Z" fill="#9b2c2c" stroke="#742a2a" strokeWidth="1"/>
        </svg>
      )
    },
    {
      id: 'reamer',
      name: 'Reamer',
      svg: (
        <svg viewBox="0 0 100 100" className="w-20 h-20">
          <defs>
            <linearGradient id="reamerGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#d69e2e" />
              <stop offset="100%" stopColor="#975a16" />
            </linearGradient>
          </defs>
          <rect x="43" y="0" width="14" height="20" fill="#975a16"/>
          <rect x="40" y="20" width="20" height="45" fill="url(#reamerGrad)" stroke="#744210" strokeWidth="1"/>
          <path d="M 40 30 L 30 37 L 35 50 L 40 50 Z" fill="#ecc94b" stroke="#744210" strokeWidth="1"/>
          <path d="M 60 30 L 70 37 L 65 50 L 60 50 Z" fill="#ecc94b" stroke="#744210" strokeWidth="1"/>
          <path d="M 40 50 L 30 57 L 35 70 L 40 65 Z" fill="#ecc94b" stroke="#744210" strokeWidth="1"/>
          <path d="M 60 50 L 70 57 L 65 70 L 60 65 Z" fill="#ecc94b" stroke="#744210" strokeWidth="1"/>
          <rect x="43" y="65" width="14" height="35" fill="#975a16"/>
        </svg>
      )
    },
    {
      id: 'cross_over',
      name: 'Cross-over Sub',
      svg: (
        <svg viewBox="0 0 100 100" className="w-20 h-20">
          <defs>
            <linearGradient id="crossGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#805ad5" />
              <stop offset="100%" stopColor="#553c9a" />
            </linearGradient>
          </defs>
          <rect x="38" y="0" width="24" height="25" fill="#6b46c1" stroke="#44337a" strokeWidth="1"/>
          <path d="M 38 25 L 40 55 L 60 55 L 62 25 Z" fill="url(#crossGrad)" stroke="#44337a" strokeWidth="1"/>
          <line x1="40" y1="38" x2="60" y2="38" stroke="#9f7aea" strokeWidth="1"/>
          <line x1="40" y1="45" x2="60" y2="45" stroke="#9f7aea" strokeWidth="1"/>
          <rect x="42" y="55" width="16" height="45" fill="#6b46c1" stroke="#44337a" strokeWidth="1"/>
        </svg>
      )
    },
    {
      id: 'other',
      name: 'Other',
      svg: (
        <svg viewBox="0 0 100 100" className="w-20 h-20">
          <defs>
            <linearGradient id="otherGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#718096" />
              <stop offset="100%" stopColor="#4a5568" />
            </linearGradient>
          </defs>
          <rect x="42" y="0" width="16" height="100" fill="url(#otherGrad)" stroke="#2d3748" strokeWidth="1"/>
          <text x="50" y="55" fontSize="32" fill="#e2e8f0" textAnchor="middle" fontWeight="bold">?</text>
        </svg>
      )
    }
  ];

  return (
    <div className="bg-gray-900 min-h-screen">
      <h1 className="text-3xl font-bold text-white pt-8 pb-8 text-center">
        Bottom Hole Assembly Components
      </h1>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8 max-w-6xl mx-auto">
        {icons.map((icon) => (
          <div
            key={icon.id}
            className="flex flex-col items-center bg-gray-800 rounded-lg shadow-lg hover:bg-gray-700 transition-colors"
          >
            <div className="bg-white rounded-lg">
              {icon.svg}
            </div>
            <h3 className="text-sm font-semibold text-white text-center mb-1">
              {icon.name}
            </h3>
            <code className="text-xs text-gray-400 bg-gray-900 rounded mb-2">
              {icon.id}
            </code>
          </div>
        ))}
      </div>
      <div className="mt-12 max-w-4xl mx-auto bg-gray-800 rounded-lg">
        <h2 className="text-xl font-bold text-white mb-4">Usage</h2>
        <p className="text-gray-300 mb-4">
          You can copy the SVG code for each icon by clicking on it. Each icon is designed to represent the specific component in a bottom hole assembly used in oil and gas drilling operations.
        </p>
        <div className="bg-gray-900 rounded text-sm text-gray-300 font-mono overflow-x-auto">
          <div>• Drill Bit - Cutting tool at the bottom</div>
          <div>• Stabilizer - Maintains hole alignment</div>
          <div>• Drill Collar - Provides weight on bit</div>
          <div>• Heavy Weight Drill Pipe - Transition between collar and pipe</div>
          <div>• Drill Pipe - Main drilling conduit</div>
          <div>• Jar - Provides upward/downward impact</div>
          <div>• MWD Tool - Measurement while drilling</div>
          <div>• Downhole Motor - Rotates the bit</div>
          <div>• Reamer - Enlarges the borehole</div>
          <div>• Cross-over Sub - Connects different thread sizes</div>
        </div>
      </div>
    </div>
  );
};

export default BHAIcons;