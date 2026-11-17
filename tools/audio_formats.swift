// Lists CoreAudio formats of the C-Media dongles (name contains "Cable"; edit the filter for "USB Audio Device").
// Run: swift tools/audio_formats.swift   (used for docs/SOUND_CARD.md, 2026-11-17)
import CoreAudio
func get<T>(_ id: AudioObjectID, _ sel: AudioObjectPropertySelector, _ scope: AudioObjectPropertyScope = kAudioObjectPropertyScopeGlobal, _ def: T) -> [T] {
  var a = AudioObjectPropertyAddress(mSelector: sel, mScope: scope, mElement: kAudioObjectPropertyElementMain)
  var size: UInt32 = 0
  guard AudioObjectGetPropertyDataSize(id, &a, 0, nil, &size) == noErr, size > 0 else { return [] }
  var arr = [T](repeating: def, count: Int(size) / MemoryLayout<T>.stride)
  AudioObjectGetPropertyData(id, &a, 0, nil, &size, &arr); return arr
}
for d in get(AudioObjectID(kAudioObjectSystemObject), kAudioHardwarePropertyDevices, kAudioObjectPropertyScopeGlobal, AudioObjectID(0)) {
  let n = get(d, kAudioObjectPropertyName, kAudioObjectPropertyScopeGlobal, Unmanaged<CFString>?.none).first??.takeUnretainedValue() as String? ?? ""
  guard n.contains("Cable") else { continue }
  let uid = get(d, kAudioDevicePropertyDeviceUID, kAudioObjectPropertyScopeGlobal, Unmanaged<CFString>?.none).first??.takeUnretainedValue() as String? ?? ""
  print("name:", n, "uid:", uid, "id:", d)
  for r in get(d, kAudioDevicePropertyAvailableNominalSampleRates, kAudioObjectPropertyScopeGlobal, AudioValueRange()) { print(" rate", r.mMinimum, r.mMaximum) }
  for (s, l) in [(kAudioObjectPropertyScopeInput, "in"), (kAudioObjectPropertyScopeOutput, "out")] {
    for f in get(d, kAudioStreamPropertyAvailablePhysicalFormats, s, AudioStreamRangedDescription()) {
      _ = f
    }
    for st in get(d, kAudioDevicePropertyStreams, s, AudioObjectID(0)) {
      for f in get(st, kAudioStreamPropertyAvailablePhysicalFormats, kAudioObjectPropertyScopeGlobal, AudioStreamRangedDescription()) {
        print(" \(l) fmt rate \(f.mFormat.mSampleRate) ch \(f.mFormat.mChannelsPerFrame) bits \(f.mFormat.mBitsPerChannel)")
      }
    }
  }
}
