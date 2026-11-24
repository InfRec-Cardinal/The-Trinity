                                                                                                               
                                                                                           
import Carbon
import Foundation

func currentID() -> String {
    let src = TISCopyCurrentKeyboardInputSource().takeRetainedValue()
    guard let p = TISGetInputSourceProperty(src, kTISPropertyInputSourceID) else { return "" }
    return Unmanaged<CFString>.fromOpaque(p).takeUnretainedValue() as String
}

let args = CommandLine.arguments
if args.count >= 2 && args[1] == "get" { print(currentID()); exit(0) }
guard args.count >= 3 && args[1] == "set" else { fputs("usage: inputsource get | set <id>\n", stderr); exit(64) }
let filter = [kTISPropertyInputSourceID as String: args[2]] as CFDictionary
guard let list = TISCreateInputSourceList(filter, false)?.takeRetainedValue() as? [TISInputSource], let src = list.first else {
    fputs("input source \(args[2]) not enabled\n", stderr); exit(2)
}
let status = TISSelectInputSource(src)
print(status == noErr ? "selected \(currentID())" : "error \(status)")
exit(status == noErr ? 0 : 1)
