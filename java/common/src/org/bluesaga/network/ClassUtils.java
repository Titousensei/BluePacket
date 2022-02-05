package org.bluesaga.network;

import java.io.*;
import java.util.*;
import java.lang.reflect.*;
import java.net.URL;
import java.net.JarURLConnection;
import java.util.jar.*;
import java.util.zip.*;


public interface ClassUtils
{
  public static List<Field> getSortedFields(Class<?> cl)
  {
    List<Field> lf = Arrays.asList(cl.getDeclaredFields());
    lf.sort(Comparator.comparing(Field::getName));
    return lf;
  }

  /**
   * From https://github.com/tnm/murmurhash-java/blob/master/src/main/java/ie/ucd/murmur/MurmurHash.java
   * Public Domain
   */
  @SuppressWarnings({"fallthrough"})
  public static int murmur32(final byte[] data)
  {
    // 'm' and 'r' are mixing constants generated offline.
    // They're not really 'magic', they just happen to work well.
    final int m = 0x5bd1e995;
    final int r = 24;

    int length = data.length;
    int seed = 0x9747b28c;
    // Initialize the hash to a random value
    int h = seed^length;
    int length4 = length/4;

    for (int i=0; i<length4; i++) {
        final int i4 = i*4;
        int k = (data[i4+0]&0xff) +((data[i4+1]&0xff)<<8)
                +((data[i4+2]&0xff)<<16) +((data[i4+3]&0xff)<<24);
        k *= m;
        k ^= k >>> r;
        k *= m;
        h *= m;
        h ^= k;
    }

    // Handle the last few bytes of the input array
    switch (length%4) {
    case 3: h ^= (data[(length&~3) +2]&0xff) << 16;
    case 2: h ^= (data[(length&~3) +1]&0xff) << 8;
    case 1: h ^= (data[length&~3]&0xff);
            h *= m;
    }

    h ^= h >>> 13;
    h *= m;
    h ^= h >>> 15;

    return h;
  }

  static <T> void addIfSubClass(Collection<Class<? extends T>> result, String classname, Class<T> baseclass)
  {
    try {
      Class<?> cl = Class.forName(classname);
      if (Class.forName(classname).getDeclaringClass() != null) return;
      if (baseclass.isAssignableFrom(cl)) {
        Class<? extends T> clazz = cl.asSubclass(baseclass);
        if (!baseclass.equals(clazz)) {
          result.add(clazz);
        }
      }
    }
    catch (Exception ex) {
       throw new RuntimeException(ex);
    }
  }

  static <T> void findInDirectory(Collection<Class<? extends T>> result,
        int rootDirLength, File directory, Class<T> baseclass)
  {
    File[] files = directory.listFiles();
    for (int i=0 ; i<files.length ; i++) {
      if (files[i].isDirectory()) {
        findInDirectory(result, rootDirLength, files[i], baseclass);
      }
      else {
        String path = files[i].getPath();
        if (path.endsWith(".class")) {
          String classname = path.substring(rootDirLength, path.length()-6);
          addIfSubClass(result, classname.replace('/','.'), baseclass);
        }
      }
    }
  }

  public static <T> Collection<Class<? extends T>> findSubClasses(String root_package, Class<T> baseclass)
  {
    Collection<Class<? extends T>> result = new ArrayList<>();
    Set<URL> discoverable_urls = new HashSet<>();
    discoverable_urls.add(ClassUtils.class.getResource(root_package));

    try {
      ClassLoader loader = ClassUtils.class.getClassLoader();
      for (Enumeration<URL> u = loader.getResources(root_package); u.hasMoreElements();) {
        discoverable_urls.add(u.nextElement());
      }
    }
    catch (IOException ex) {
      throw new RuntimeException(ex);
    }
    
    try {
      for (URL url : discoverable_urls) {
        if (url == null) continue;
        File directory = new File(url.getFile());
        if (directory.exists()) {
          int rootDirLength = directory.getAbsolutePath().length() - root_package.length();
          findInDirectory(result, rootDirLength, directory, baseclass);
        }
        else { // jar file
          JarURLConnection conn = (JarURLConnection) url.openConnection();
          String starts = conn.getEntryName();
          Enumeration<JarEntry> e = conn.getJarFile().entries();
          while (e.hasMoreElements()) {
            String entryname = e.nextElement().getName();
            if (entryname.startsWith(starts) && entryname.endsWith(".class")) {
              String classname = entryname.substring(0,entryname.length()-6);
              if (classname.startsWith("/")) {
                  classname = classname.substring(1);
              }
              classname = classname.replace('/','.');
              addIfSubClass(result, classname, baseclass);
            }
          }
        }
      }
    }
    catch (IOException ex) {
      throw new RuntimeException(ex);
    }
    return result;
  }
}
