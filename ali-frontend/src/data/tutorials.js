export const tutorials = [
    {
        id: 1,
        title: "Mastering TikTok Ads Algorithm",
        category: "Paid Social",
        duration: "10 min",
        // Content tailored for different styles
        modes: {
            text: `
        ## How the Algorithm Works
        The TikTok algorithm prioritizes **watch time** and **completion rate**.
        
        ### Key Metrics:
        1. **CTR (Click-Through Rate):** Should be above 1.5%.
        2. **Hook Rate:** % of people watching first 3s.
        
        To optimize, focus on the first 2 seconds of your creative.
      `,
            video: "https://storage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4", // Placeholder
            audio: "https://www2.cs.uic.edu/~i101/SoundFiles/BabyElephantWalk60.wav" // Placeholder
        }
    },
    {
        id: 2,
        title: "Google Ads Bidding Strategies",
        category: "SEM",
        duration: "15 min",
        modes: {
            text: `
        ## Manual CPC vs. Smart Bidding
        * **Manual CPC:** Maximum control, high maintenance.
        * **Target CPA:** Best for scaling stable accounts.
        
        **Recommendation:** Start with Max Clicks to gather data, then switch to Target ROAS.
      `,
            video: "https://storage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
            audio: "https://www2.cs.uic.edu/~i101/SoundFiles/CantinaBand3.wav"
        }
    }
];