package test;

import java.io.*;
import org.bluepacket.BluePacket;

public class ListPacketTestGen {
    public static void main(String[] args) throws Exception {
        // Test 1: OuterContainer with list DemoOuter (monomorphic)
        OuterContainer oc = new OuterContainer();
        oc.setOuterList(new DemoOuter[] {
            new DemoOuter().setOInt(1).setOString("a"),
            new DemoOuter().setOInt(2).setOString("b")
        });
        byte[] ocData = oc.serialize();
        System.out.println("OuterContainer (list DemoOuter) length: " + ocData.length);
        System.out.println("Hex: " + bytesToHex(ocData));
        writeFile("OuterContainer.bin", ocData);

        // Test 2: PolyContainer with list packet (polymorphic) - empty list
        PolyContainer pc = new PolyContainer();
        pc.setPolyList(new BluePacket[0]);
        byte[] pcEmpty = pc.serialize();
        System.out.println("\nPolyContainer (list packet) empty length: " + pcEmpty.length);
        System.out.println("Hex: " + bytesToHex(pcEmpty));
        writeFile("PolyContainerEmpty.bin", pcEmpty);

        // Test 3: PolyContainer with list packet containing PacketA and PacketB
        // Note: PacketA and PacketB don't exist in this test, so we'll use DemoOuter and DemoPacket
        // Actually, let's just use DemoOuter since it's available
        PolyContainer pc2 = new PolyContainer();
        pc2.setPolyList(new BluePacket[] {
            new DemoOuter().setOInt(10).setOString("x"),
            new DemoOuter().setOInt(20).setOString("y")
        });
        byte[] pcData = pc2.serialize();
        System.out.println("\nPolyContainer (list packet with 2 DemoOuter) length: " + pcData.length);
        System.out.println("Hex: " + bytesToHex(pcData));
        writeFile("PolyContainer.bin", pcData);
    }

    private static void writeFile(String name, byte[] data) throws IOException {
        try (FileOutputStream out = new FileOutputStream(name)) {
            out.write(data);
        }
    }

    private static String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}