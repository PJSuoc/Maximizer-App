export const COLOR_BG = '#F2F3F4';
export const COLOR_HOVER = '#FFFFFF';
export const COLOR_DEMOCRACY = '#9277DE';
export const COLOR_PRESIDENT = '#F5928D';
export const COLOR_SENATE = '#fec548';
export const COLOR_HOUSE = '#B4CDE3';
export const COLOR_GOVERNOR = '#13DDB7';
export const COLOR_STATE_LEGISLATURE = '#D19E9B';
export const COLOR_ABORTION = '#F768A0';
export const COLOR_KEY_BALLOT = '#13DDB7';
export const COLOR_DEFAULT = '#e1e1e1';
export const COLOR_BORDER = '#EEEEEE';
export const COLOR_BORDER_LEG = '#000000';

function interpolateColor(color1, color2, factor) {
    const result = color1.slice();
    for (let i = 0; i < 3; i++) {
        result[i] = Math.round(result[i] + factor * (color2[i] - color1[i]));
    }
    return result;
}

function hexToRgb(hex) {
    const bigint = parseInt(hex.slice(1), 16);
    return [(bigint >> 16) & 255, (bigint >> 8) & 255, bigint & 255];
}

function rgbToHex(rgb) {
    return "#" + rgb.map(x => {
        const hex = x.toString(16);
        return hex.length === 1 ? "0" + hex : hex;
    }).join('');
}

export function interpolateColors(startColor, endColor, steps, extendRange = false) {
      // Combined function for both cases
        const start = hexToRgb(startColor);
        const end = hexToRgb(endColor);
        const colors = [];

        if (extendRange) {
            // Case 2: Create a darker version of the end color
            const darkerEnd = end.map(c => Math.max(0, c - 40));
            steps += 1; // Add an extra step for the darker color

            for (let i = 0; i < steps; i++) {
                const factor = i / (steps - 1);
                const interpolated = i === steps - 1 
                    ? darkerEnd 
                    : interpolateColor(start, end, factor);
                colors.push(rgbToHex(interpolated));
            }
        } else {
            // Case 1: Standard interpolation
            for (let i = 0; i < steps; i++) {
                const factor = i / (steps - 1);
                const interpolated = interpolateColor(start, end, factor);
                colors.push(rgbToHex(interpolated));
            }
        }

    return colors;
}

export const democracyScale = interpolateColors(COLOR_DEFAULT, COLOR_DEMOCRACY, 5);
export const presidentScale = interpolateColors(COLOR_DEFAULT, COLOR_PRESIDENT, 5);
export const houseScale = interpolateColors(COLOR_DEFAULT, COLOR_HOUSE, 5);
export const senateScale = [
    "#e1e1e1", "#eedcb4", "#ffd885", "#ffce65", "#fec548"
];
export const governorScale = interpolateColors(COLOR_DEFAULT, COLOR_GOVERNOR, 5);
export const stateLegScale = interpolateColors(COLOR_DEFAULT, COLOR_STATE_LEGISLATURE, 5);
export const abortionScale = interpolateColors(COLOR_DEFAULT, COLOR_ABORTION, 5);
export const keyBallotScale = interpolateColors(COLOR_DEFAULT, COLOR_KEY_BALLOT, 5);