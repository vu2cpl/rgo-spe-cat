// Prints volume, dB range and mute of a CoreAudio device by ID (IDs: run audio_formats.swift).
// Run: swift tools/audio_levels.swift <device-id>   (used for docs/SOUND_CARD.md, 2026-11-17)
import CoreAudio
func f32(_ d: AudioObjectID,_ sel: AudioObjectPropertySelector,_ sc: AudioObjectPropertyScope,_ el: UInt32) -> String {
  var a = AudioObjectPropertyAddress(mSelector: sel, mScope: sc, mElement: el)
  guard AudioObjectHasProperty(d,&a) else { return "-" }
  if sel == kAudioDevicePropertyVolumeRangeDecibels { var r = AudioValueRange(); var s = UInt32(MemoryLayout<AudioValueRange>.size); AudioObjectGetPropertyData(d,&a,0,nil,&s,&r); return "\(r.mMinimum)..\(r.mMaximum) dB" }
  if sel == kAudioDevicePropertyMute { var v: UInt32 = 0; var s = UInt32(4); AudioObjectGetPropertyData(d,&a,0,nil,&s,&v); return "\(v)" }
  var v: Float32 = 0; var s = UInt32(4); AudioObjectGetPropertyData(d,&a,0,nil,&s,&v); return "\(v)"
}
let d = AudioObjectID(CommandLine.arguments[1])!
for (sc,n) in [(kAudioObjectPropertyScopeInput,"in"),(kAudioObjectPropertyScopeOutput,"out")] { for el in UInt32(0)...2 {
  print(n, el, "vol", f32(d,kAudioDevicePropertyVolumeScalar,sc,el), "dBnow", f32(d,kAudioDevicePropertyVolumeDecibels,sc,el), "range", f32(d,kAudioDevicePropertyVolumeRangeDecibels,sc,el), "mute", f32(d,kAudioDevicePropertyMute,sc,el)) } }
