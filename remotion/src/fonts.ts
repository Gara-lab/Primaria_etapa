import { loadFont as loadDisplay } from '@remotion/google-fonts/SpaceGrotesk';
import { loadFont as loadBody } from '@remotion/google-fonts/Inter';
import { loadFont as loadMono } from '@remotion/google-fonts/JetBrainsMono';
import { loadFont as loadSerif } from '@remotion/google-fonts/Spectral';
import { loadFont as loadEditorial } from '@remotion/google-fonts/SourceSerif4';

export const FONT_DISPLAY = loadDisplay('normal', { weights: ['500', '600', '700'], subsets: ['latin'] }).fontFamily;
export const FONT_BODY = loadBody('normal', { weights: ['400', '500', '600'], subsets: ['latin'] }).fontFamily;
export const FONT_MONO = loadMono('normal', { weights: ['400', '500', '700'], subsets: ['latin'] }).fontFamily;
export const FONT_SERIF = loadSerif('normal', { weights: ['500', '600'], subsets: ['latin'] }).fontFamily;
export const FONT_EDITORIAL = loadEditorial('normal', { weights: ['600', '700', '900'], subsets: ['latin'] }).fontFamily;
