package org.bluepacket;

import java.io.*;
import java.util.*;
import java.lang.reflect.*;
import java.net.URL;
import java.net.JarURLConnection;
import java.util.jar.*;
import java.util.zip.*;

/**
 * Util class to with methods to find classes in the classpath.
 */
public interface ClassUtils
{
  /**
   * Internal method to retrieve class fields sorted using reflection.
   * @param cl the class
   * @return the list of fields
   */
  public static List<Field> getSortedFields(Class<?> cl)
  {
    List<Field> lf = Arrays.asList(cl.getDeclaredFields());
    lf.sort(Comparator.comparing(Field::getName));
    return lf;
  }

  /**
   * Internal method to collect a class if it's a subclass of another.
   * Used to find all the generated classes extending BluePacket.
   * @param result the collection to update if class is a subclass
   * @param classname the name of the class to test
   * @param <T> the base class type that should be extended
   * @param baseclass the base class that should be extended
   */
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

  /**
   * Internal method to find all classes in a build directory, recursively.
   * Used to find all the generated classes extending BluePacket.
   * @param result the collection to update if class is a subclass
   * @param rootDirLength the number of characters to truncate in the absolute path
   * @param directory the directory to start looking into
   * @param <T> the base class type that should be extended
   * @param baseclass the base class that should be extended
   */
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

  /**
   * Internal method to find all subclasses in a package
   * Used to find all the generated classes extending BluePacket.
   * @param root_package the java package containing the classes to search
   * @param <T> the base class type that should be extended
   * @param baseclass the base class that should be extended
   * @return the collection of classes found
   */
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
