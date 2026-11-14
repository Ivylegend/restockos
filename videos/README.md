# RestockOS product video

## Output

Final render: [`RestockOS-Product-Demo.mp4`](RestockOS-Product-Demo.mp4), approximately 110 seconds. Raw screen capture and generated narration stay in `/tmp/restockos-video` and are not written to the repository.

## Recording workflow

1. Deploy the current app and open its hosted URL in Chrome. Confirm the public sandbox is accessible and the Treasury page shows the already verified real Testnet payment and rejection receipts.
2. Use a clean browser window in full-screen mode. Do not record the wallet approval screen, access token field, unrelated browser tabs, or private account information. The saved admin session is used only to show the seeded controls; no credential is typed during capture.
3. Run `scripts/record-product-video.sh`. It captures 103 seconds of the actual display with cursor/click emphasis, creates a calm masculine English narration with the macOS Daniel voice, adds original synthesized ambient music, captions and branded motion graphics, then crossfades an opening and closing card.
4. Follow this storyboard while the capture runs:

| Time | Screen action |
| --- | --- |
| 00–09 | Overview dashboard, metrics and stockout alerts |
| 09–20 | Inventory page, search for USB-C charger and show on-hand/reorder quantities |
| 20–31 | Procurement agent run history and low-stock signal |
| 31–44 | Open the agent page and run the interactive sandbox if no fresh simulated run exists |
| 44–57 | Suppliers page, compare the three quotes and selected supplier |
| 57–68 | Settings page, show owner spending policy and supplier allowlist without changing them |
| 68–79 | Orders page, show the clearly labeled simulated order |
| 79–92 | Treasury page, show the historical verified Testnet transaction and receipt |
| 92–103 | Show the actual on-chain rejected redirect and unchanged treasury balances |

The sandbox action may create a simulated run/order in the public demo database. It never triggers NEAR. The successful and rejected receipt IDs are existing verified Testnet evidence; the video does not fabricate transaction results or submit a new payment.

## Music and captions

The soundtrack is synthesized locally from sine-wave chord tones by FFmpeg and is original to the recording. The authored captions and narration are in `captions.json` and `voiceover.txt`. The render uses original SVG-generated title/outro cards and callouts, crossfade transitions, and burned-in captions. The renderer uses the optional `sharp` dependency already installed by Next.js and the system `ffmpeg` binary.

The video is a local file only. It is not uploaded or published to X by this script.
