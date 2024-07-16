// Make it more convenient to use (in exchange of accepting more fingerprinting)
user_pref("privacy.resistFingerprinting.letterboxing", false);
user_pref("privacy.resistFingerprinting", false);
user_pref("privacy.resistFingerprinting.pbmode", false);
user_pref("webgl.disabled", false);

// Enable userChrome.css
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);

// Enable DRM streaming
user_pref("media.eme.enabled", true)

user_pref("signon.rememberSignons", false);       // Disable ask to save password
user_pref("browser.tabs.loadInBackground", true); // Switch to new tabs
user_pref("general.autoScroll", true);            // Allow auto-scroll with middle button

// Disable Website Advertising Preferences
user_pref("dom.private-attribution.submission.enabled", false);
