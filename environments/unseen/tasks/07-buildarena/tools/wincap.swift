                                                                                                      
                                           
                                                                                                   
import AppKit
import AVFoundation
import Foundation
import ScreenCaptureKit

final class RecDelegate: NSObject, SCRecordingOutputDelegate {
    var finished: CheckedContinuation<Void, Never>?
    func recordingOutputDidFinishRecording(_ recordingOutput: SCRecordingOutput) { finished?.resume(); finished = nil }
    func recordingOutput(_ recordingOutput: SCRecordingOutput, didFailWithError error: Error) {
        fputs("recording failed: \(error)\n", stderr); finished?.resume(); finished = nil
    }
}

func waitForStopSignal() async {
    await withCheckedContinuation { (cont: CheckedContinuation<Void, Never>) in
        signal(SIGINT, SIG_IGN); signal(SIGTERM, SIG_IGN)
        let q = DispatchQueue(label: "signals")
        var resumed = false
        var sources: [DispatchSourceSignal] = []
        for sig in [SIGINT, SIGTERM] {
            let s = DispatchSource.makeSignalSource(signal: sig, queue: q)
            s.setEventHandler { if !resumed { resumed = true; cont.resume() } }
            s.resume(); sources.append(s)
        }
        objc_setAssociatedObject(q, "sources", sources, .OBJC_ASSOCIATION_RETAIN)
    }
}

@main
struct WinCap {
    static func main() async {
                                                                                                           
        _ = await MainActor.run { NSApplication.shared }
        _ = CGMainDisplayID()
        let args = CommandLine.arguments
        guard args.count >= 3, let wid = UInt32(args[1]) else { fputs("usage: wincap <windowID> <out.mov> [fps]\n", stderr); exit(64) }
        let fps = args.count >= 4 ? Int32(args[3]) ?? 30 : 30
        do {
            let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: false)
            guard let win = content.windows.first(where: { $0.windowID == wid }) else { fputs("window \(wid) not found\n", stderr); exit(2) }
            let filter = SCContentFilter(desktopIndependentWindow: win)
            let cfg = SCStreamConfiguration()
            let scale = CGFloat(filter.pointPixelScale)
            cfg.width = Int(win.frame.width * scale) / 2 * 2
            cfg.height = Int(win.frame.height * scale) / 2 * 2
            cfg.minimumFrameInterval = CMTime(value: 1, timescale: fps)
            cfg.showsCursor = false
            cfg.capturesAudio = false
            let stream = SCStream(filter: filter, configuration: cfg, delegate: nil)
            let rcfg = SCRecordingOutputConfiguration()
            rcfg.outputURL = URL(fileURLWithPath: args[2])
            rcfg.outputFileType = .mov
            rcfg.videoCodecType = .h264
            let delegate = RecDelegate()
            let rec = SCRecordingOutput(configuration: rcfg, delegate: delegate)
            try stream.addRecordingOutput(rec)
            try await stream.startCapture()
            print("recording \(cfg.width)x\(cfg.height) @\(fps)fps"); fflush(stdout)
            await waitForStopSignal()
            await withCheckedContinuation { (cont: CheckedContinuation<Void, Never>) in
                delegate.finished = cont
                Task { try? await stream.stopCapture() }
            }
            print("stopped"); fflush(stdout)
            exit(0)
        } catch {
            fputs("error: \(error)\n", stderr)
            exit(1)
        }
    }
}
